"""
PayPal Inline Checkout Views
Add these to core/views.py or create core/paypal_views.py
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import requests
import logging

logger = logging.getLogger(__name__)


def get_paypal_access_token():
    """Get PayPal OAuth access token"""
    url = f"https://api-m.{'sandbox.' if settings.PAYPAL_MODE == 'sandbox' else ''}paypal.com/v1/oauth2/token"
    
    response = requests.post(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Language": "en_US",
        },
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"}
    )
    
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        logger.error(f"PayPal auth error: {response.text}")
        return None


@login_required
@csrf_exempt  # We'll handle CSRF in the JavaScript
def create_paypal_order(request):
    """
    Create a PayPal order for weekly payment or prepay
    Called by PayPal SDK JavaScript
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        amount = data.get('amount')
        description = data.get('description', 'Baseball Pick 4 Payment')
        
        if not amount:
            return JsonResponse({'error': 'Amount required'}, status=400)
        
        # Get PayPal access token
        access_token = get_paypal_access_token()
        if not access_token:
            return JsonResponse({'error': 'PayPal authentication failed'}, status=500)
        
        # Create order
        url = f"https://api-m.{'sandbox.' if settings.PAYPAL_MODE == 'sandbox' else ''}paypal.com/v2/checkout/orders"
        
        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(amount)
                },
                "description": description
            }],
            "application_context": {
                "brand_name": "Baseball Pick 4",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
                "return_url": request.build_absolute_uri('/payments/paypal-success/'),
                "cancel_url": request.build_absolute_uri('/payments/')
            }
        }
        
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            },
            json=order_data
        )
        
        if response.status_code == 201:
            order = response.json()
            logger.info(f"PayPal order created: {order['id']} for user {request.user.username}")
            return JsonResponse({'orderID': order['id']})
        else:
            logger.error(f"PayPal order creation failed: {response.text}")
            return JsonResponse({'error': 'Order creation failed'}, status=500)
            
    except Exception as e:
        logger.error(f"PayPal order error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@csrf_exempt
def capture_paypal_order(request):
    """
    Capture/complete a PayPal order after user approval
    Called by PayPal SDK JavaScript
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        order_id = data.get('orderID')
        payment_type = data.get('payment_type', 'weekly')  # 'weekly', 'season_prepay', 'custom_prepay'
        
        if not order_id:
            return JsonResponse({'error': 'Order ID required'}, status=400)
        
        # Get PayPal access token
        access_token = get_paypal_access_token()
        if not access_token:
            return JsonResponse({'error': 'PayPal authentication failed'}, status=500)
        
        # Capture the order
        url = f"https://api-m.{'sandbox.' if settings.PAYPAL_MODE == 'sandbox' else ''}paypal.com/v2/checkout/orders/{order_id}/capture"
        
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if response.status_code == 201:
            capture_data = response.json()
            
            # Verify payment was successful
            if capture_data['status'] == 'COMPLETED':
                amount = float(capture_data['purchase_units'][0]['payments']['captures'][0]['amount']['value'])
                
                # Process based on payment type
                if payment_type == 'weekly':
                    # Create WeeklyPayment record
                    from core.models import WeeklyPayment, Week
                    
                    team_membership = request.user.team_memberships.filter(status='active').first()
                    current_week = Week.objects.filter(is_active=True).first()
                    
                    if team_membership and current_week:
                        WeeklyPayment.objects.create(
                            user=request.user,
                            week=current_week,
                            team=team_membership.team,
                            amount=amount,
                            payment_method='paypal',
                            status='completed',
                            stripe_payment_intent_id=f'paypal_{order_id}',
                        )
                        
                        logger.info(f"Weekly PayPal payment completed: {request.user.username} - ${amount}")
                        return JsonResponse({
                            'status': 'success',
                            'redirect': '/make-picks/'
                        })
                
                elif payment_type == 'season_prepay':
                    # Process season prepay
                    from core.services.balance_service import complete_season_prepay
                    
                    team_membership = request.user.team_memberships.filter(status='active').first()
                    weeks_covered = data.get('weeks_covered', 26)
                    
                    if team_membership:
                        success = complete_season_prepay(
                            user=request.user,
                            amount_paid=amount,
                            weeks_covered=weeks_covered,
                            team=team_membership.team
                        )
                        
                        if success:
                            logger.info(f"Season prepay completed via PayPal: {request.user.username} - ${amount}")
                            return JsonResponse({
                                'status': 'success',
                                'redirect': '/'
                            })
                
                elif payment_type == 'custom_prepay':
                    # Process custom prepay
                    from core.services.balance_service import complete_custom_prepay
                    
                    team_membership = request.user.team_memberships.filter(status='active').first()
                    
                    if team_membership:
                        success = complete_custom_prepay(
                            user=request.user,
                            amount_paid=amount,
                            team=team_membership.team
                        )
                        
                        if success:
                            logger.info(f"Custom prepay completed via PayPal: {request.user.username} - ${amount}")
                            return JsonResponse({
                                'status': 'success',
                                'redirect': '/'
                            })
                
                return JsonResponse({'error': 'Payment processing failed'}, status=500)
            else:
                logger.error(f"PayPal capture failed: {capture_data['status']}")
                return JsonResponse({'error': 'Payment not completed'}, status=400)
        else:
            logger.error(f"PayPal capture error: {response.text}")
            return JsonResponse({'error': 'Capture failed'}, status=500)
            
    except Exception as e:
        logger.error(f"PayPal capture error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)