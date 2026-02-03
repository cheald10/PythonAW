"""
Baseball Pick 4 - Django Admin Configuration
Admin interfaces for all models

Created: January 22, 2026
Sprint: Sprint 2, Days 6-8
"""

from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Count, Sum, Q
from .models import (
    UserProfile,
    Team,
    TeamMember,
    TeamInvitation,
    Week,
    MLBPlayer,
    PickCategory,
    Pick,
    WeeklyResult,
    WeeklyPayment,
    WeeklyPrizePool,
    WeeklyPayout,
    SeasonPot,
    SeasonPayout,
    CompanyFee,
    TeamStanding,
    UserStanding,
)

# ==============================================================================
# GET USER MODEL
# ==============================================================================

User = get_user_model()

# Only unregister if User is already registered (handles both default and custom user models)
if admin.site.is_registered(User):
    admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    class Media:
        js = ("admin/js/passwords.js",)

    fieldsets = UserAdmin.fieldsets + (
        ("Terms & Verification", {
            "fields": ("terms_accepted", "terms_accepted_at"),
        }),
    )

# ==============================================================================
# USER PROFILE
# ==============================================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'timezone',
        'preferred_payout_method',
        'total_lifetime_winnings',
        'total_lifetime_paid',
        'net_profit_display',
    ]
    list_filter = ['timezone', 'preferred_payout_method']
    search_fields = ['user__username', 'user__email', 'venmo_username', 'paypal_email']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User Info', {
            'fields': ('user', 'timezone', 'phone_number')
        }),
        ('Payment Info', {
            'fields': (
                'preferred_payout_method',
                'venmo_username',
                'paypal_email',
                'stripe_customer_id',
            )
        }),
        ('Lifetime Stats', {
            'fields': (
                'total_lifetime_winnings',
                'total_lifetime_paid',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def net_profit_display(self, obj):
        profit = obj.net_profit
        color = 'green' if profit >= 0 else 'red'
        return format_html(
            '<span style="color: {};">${}</span>',
            color,
            f'{profit:.2f}'
        )
    net_profit_display.short_description = 'Net Profit'


# ==============================================================================
# TEAM MANAGEMENT
# ==============================================================================

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'season_year',
        'captain',
        'weekly_fee',
        'member_count_display',
        'is_ready_display',
        'is_public',
        'is_active',
        'join_code',
    ]
    list_filter = ['season_year', 'weekly_fee', 'is_public', 'is_active']
    search_fields = ['name', 'captain__username', 'join_code']
    readonly_fields = ['slug', 'join_code', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'description', 'captain', 'season_year', 'logo_url')
        }),
        ('Settings', {
            'fields': (
                'weekly_fee',
                'is_public',
                'is_active',
                'min_members',
                'max_members',
                'join_code',
            )
        }),
        ('Payment Integration', {
            'fields': (
                'auto_payout_enabled',
                'stripe_connected_account_id',
                'paypal_email',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def member_count_display(self, obj):
        count = obj.member_count
        return f"{count} members"
    member_count_display.short_description = 'Members'

    def is_ready_display(self, obj):
        ready = obj.is_ready
        color = 'green' if ready else 'red'
        text = '✓ Ready' if ready else '✗ Not Ready'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            text
        )
    is_ready_display.short_description = 'Status'


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'role', 'status', 'joined_at']
    list_filter = ['role', 'status', 'team']
    search_fields = ['user__username', 'team__name']
    readonly_fields = ['joined_at', 'created_at']

    fieldsets = (
        ('Membership', {
            'fields': ('team', 'user', 'role', 'status')
        }),
        ('Removal Info', {
            'fields': ('removed_at', 'removed_by', 'notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('joined_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = [
        'team',
        'invited_user_email',
        'invitation_type',
        'status',
        'invited_by',
        'expires_at',
        'is_expired_display',
    ]
    list_filter = ['invitation_type', 'status', 'team']
    search_fields = ['invited_user_email', 'team__name', 'invited_by__username']
    readonly_fields = ['token', 'created_at', 'updated_at', 'expires_at']

    fieldsets = (
        ('Invitation Info', {
            'fields': (
                'team',
                'invited_by',
                'invited_user_email',
                'invited_user',
                'invitation_type',
                'status',
            )
        }),
        ('Details', {
            'fields': ('token', 'message', 'expires_at', 'responded_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_expired_display(self, obj):
        expired = obj.is_expired
        if expired:
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Active</span>')
    is_expired_display.short_description = 'Expiration'


# ==============================================================================
# GAME CORE
# ==============================================================================

@admin.register(Week)
class WeekAdmin(admin.ModelAdmin):
    list_display = [
        'week_number',
        'season_year',
        'saturday_date',
        'deadline_utc',
        'is_active',
        'is_completed',
        'is_past_deadline_display',
    ]
    list_filter = ['season_year', 'is_active', 'is_completed']
    search_fields = ['week_number', 'season_year']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Week Info', {
            'fields': (
                'week_number',
                'season_year',
                'saturday_date',
                'deadline_utc',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'is_completed',
                'games_start_time',
                'games_end_time',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def is_past_deadline_display(self, obj):
        past = obj.is_past_deadline
        if past:
            return format_html('<span style="color: red;">Closed</span>')
        return format_html('<span style="color: green;">Open</span>')
    is_past_deadline_display.short_description = 'Picks'


@admin.register(MLBPlayer)
class MLBPlayerAdmin(admin.ModelAdmin):
    list_display = [
        'full_name',
        'team_abbreviation',
        'position',
        'is_pitcher',
        'is_two_way_player',
        'is_active',
    ]
    list_filter = [
        'is_active',
        'is_pitcher',
        'is_two_way_player',
        'team_abbreviation',
        'position',
    ]
    search_fields = ['full_name', 'first_name', 'last_name', 'team_name']
    readonly_fields = ['last_updated', 'created_at']

    fieldsets = (
        ('Player Info', {
            'fields': (
                'mlb_player_id',
                'first_name',
                'last_name',
                'full_name',
                'jersey_number',
            )
        }),
        ('Team Info', {
            'fields': (
                'team_name',
                'team_abbreviation',
                'mlb_team_id',
            )
        }),
        ('Position', {
            'fields': (
                'position',
                'is_pitcher',
                'is_two_way_player',
                'is_active',
            )
        }),
        ('Timestamps', {
            'fields': ('last_updated', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PickCategory)
class PickCategoryAdmin(admin.ModelAdmin):
    list_display = [
        'display_order',
        'code',
        'name',
        'requires_pitcher',
        'is_active',
        'icon',
        'color',
    ]
    list_filter = ['requires_pitcher', 'is_active']
    search_fields = ['code', 'name']
    ordering = ['display_order']

    fieldsets = (
        ('Category Info', {
            'fields': ('code', 'name', 'description', 'requires_pitcher')
        }),
        ('Display', {
            'fields': ('display_order', 'icon', 'color', 'is_active')
        }),
    )


@admin.register(Pick)
class PickAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'team',
        'week',
        'category',
        'player',
        'result_status',
        'points_earned',
        'submitted_at',
    ]
    list_filter = [
        'result_status',
        'week',
        'category',
        'team',
    ]
    search_fields = [
        'user__username',
        'player__full_name',
        'team__name',
    ]
    readonly_fields = ['submitted_at', 'scored_at', 'created_at']

    fieldsets = (
        ('Pick Info', {
            'fields': (
                'user',
                'team',
                'week',
                'category',
                'player',
            )
        }),
        ('Cross-Team Copying', {
            'fields': ('copied_from_team', 'is_auto_copied'),
            'classes': ('collapse',)
        }),
        ('Scoring', {
            'fields': (
                'result_status',
                'points_earned',
                'scored_at',
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': ('submitted_at', 'created_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WeeklyResult)
class WeeklyResultAdmin(admin.ModelAdmin):
    list_display = [
        'week',
        'player',
        'category',
        'achieved_display',
        'stat_value',
        'game_date',
        'verified_display',
    ]
    list_filter = [
        'achieved',
        'week',
        'category',
        'game_date',
    ]
    search_fields = [
        'player__full_name',
        'game_id',
    ]
    readonly_fields = ['created_at']

    fieldsets = (
        ('Result Info', {
            'fields': (
                'week',
                'player',
                'category',
                'achieved',
                'stat_value',
            )
        }),
        ('Game Info', {
            'fields': (
                'game_date',
                'game_id',
                'opponent_team',
            )
        }),
        ('Verification', {
            'fields': (
                'verified_at',
                'verified_by',
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def achieved_display(self, obj):
        if obj.achieved:
            return format_html('<span style="color: green; font-weight: bold;">✓ YES</span>')
        return format_html('<span style="color: red;">✗ NO</span>')
    achieved_display.short_description = 'Achieved'

    def verified_display(self, obj):
        if obj.verified_at:
            return format_html('<span style="color: green;">✓ Verified</span>')
        return format_html('<span style="color: orange;">Pending</span>')
    verified_display.short_description = 'Status'


# ==============================================================================
# FINANCIAL
# ==============================================================================



# ==============================================================================
# FINANCIAL - ENHANCED PAYMENT MANAGEMENT
# ==============================================================================

@admin.register(WeeklyPayment)
class WeeklyPaymentAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for managing weekly payments
    Provides comprehensive payment tracking and management with statistics
    """
    list_display = [
        'id',
        'user',
        'team',
        'week_display',
        'amount_display',
        'payment_status',
        'payment_method',
        'payment_date',
        'stripe_link',
    ]
    list_filter = [
        'payment_status',
        'payment_method',
        'team',
        'week__season_year',
        'payment_date',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'team__name',
        'stripe_payment_intent_id',
        'stripe_charge_id',
        'paypal_transaction_id',
        'notes',
    ]
    readonly_fields = [
        'payment_date',
        'stripe_payment_intent_id',
        'stripe_charge_id',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'payment_date'
    list_per_page = 50

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'user',
                'team',
                'week',
                'amount',
                'payment_status',
                'payment_method',
                'payment_date',
            )
        }),
        ('Stripe Details', {
            'fields': (
                'stripe_payment_intent_id',
                'stripe_charge_id',
                'stripe_customer_id',
            ),
            'classes': ('collapse',)
        }),
        ('PayPal Details', {
            'fields': (
                'paypal_transaction_id',
            ),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': (
                'external_transaction_id',
                'last_payment_error',
                'recorded_by',
                'notes',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # Custom actions
    actions = ['mark_as_completed', 'mark_as_failed', 'export_to_csv']

    def week_display(self, obj):
        """Display week number with season year"""
        return f"Week {obj.week.week_number} ({obj.week.season_year})"
    week_display.short_description = 'Week'
    week_display.admin_order_field = 'week__week_number'

    def amount_display(self, obj):
        """Display amount with color coding by status"""
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'failed': 'red',
            'refunded': 'blue',
        }
        color = colors.get(obj.payment_status, 'black')
        amount_str = f'{obj.amount:.2f}'  # ✅ Format first
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span>',
            color,
            amount_str  # ✅ Then pass the string
        )
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def stripe_link(self, obj):
        """Display Stripe charge ID with link to dashboard"""
        if obj.stripe_charge_id:
            stripe_url = f'https://dashboard.stripe.com/payments/{obj.stripe_charge_id}'
            return format_html(
                '<a href="{}" target="_blank" title="View in Stripe Dashboard">{}</a>',
                stripe_url,
                obj.stripe_charge_id[:20] + '...' if len(obj.stripe_charge_id) > 20 else obj.stripe_charge_id
            )
        return '-'
    stripe_link.short_description = 'Stripe'

    # Custom admin actions
    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed"""
        updated = queryset.update(payment_status='completed')
        self.message_user(
            request,
            f'{updated} payment(s) marked as completed.'
        )
    mark_as_completed.short_description = 'Mark selected payments as completed'

    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed"""
        updated = queryset.update(payment_status='failed')
        self.message_user(
            request,
            f'{updated} payment(s) marked as failed.'
        )
    mark_as_failed.short_description = 'Mark selected payments as failed'

    def export_to_csv(self, request, queryset):
        """Export selected payments to CSV"""
        import csv
        from django.http import HttpResponse
        from datetime import datetime

        response = HttpResponse(content_type='text/csv')
        filename = f'payments_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Date', 'User', 'Email', 'Team', 'Week',
            'Amount', 'Status', 'Method', 'Stripe ID', 'Notes'
        ])

        for payment in queryset:
            writer.writerow([
                payment.id,
                payment.payment_date.strftime('%Y-%m-%d %H:%M:%S') if payment.payment_date else '',
                payment.user.username,
                payment.user.email,
                payment.team.name,
                f'Week {payment.week.week_number}',
                payment.amount,
                payment.get_payment_status_display(),
                payment.get_payment_method_display(),
                payment.stripe_charge_id or '',
                payment.notes or '',
            ])

        self.message_user(
            request,
            f'{queryset.count()} payment(s) exported to CSV.'
        )
        return response
    export_to_csv.short_description = 'Export selected payments to CSV'

    def get_queryset(self, request):
        """Optimize queries with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'team', 'week')

    def changelist_view(self, request, extra_context=None):
        """Add payment statistics to the top of the list view"""
        extra_context = extra_context or {}

        # Calculate statistics
        payments = self.get_queryset(request)

        extra_context['total_payments'] = payments.count()
        extra_context['total_collected'] = payments.filter(
            payment_status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        extra_context['pending_amount'] = payments.filter(
            payment_status='pending'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        extra_context['completed_count'] = payments.filter(
            payment_status='completed'
        ).count()
        extra_context['pending_count'] = payments.filter(
            payment_status='pending'
        ).count()
        extra_context['failed_count'] = payments.filter(
            payment_status='failed'
        ).count()

        return super().changelist_view(request, extra_context)


@admin.register(WeeklyPrizePool)
class WeeklyPrizePoolAdmin(admin.ModelAdmin):
    """
    Enhanced admin interface for managing weekly prize pools
    Shows pot accumulation, distribution, and payment statistics
    """
    list_display = [
        'id',
        'team',
        'week_display',
        'total_collected_display',
        'weekly_pool_amount_display',
        'company_fee_display',
        'payment_count_display',
        'num_perfect_picks',
        'is_distributed',
    ]
    list_filter = [
        'team',
        'week__season_year',
        'is_distributed',
    ]
    search_fields = [
        'team__name',
        'week__week_number',
    ]
    readonly_fields = [
        'created_at',
        'scored_at',
        'payment_count_display',
        'average_payment_display',
    ]

    fieldsets = (
        ('Pool Information', {
            'fields': (
                'team',
                'week',
                'total_collected',
            )
        }),
        ('Money Breakdown', {
            'fields': (
                'rollover_from_previous',
                'weekly_pool_amount',
                'season_pot_contribution',
                'company_fee',
                'per_pick_value',
            )
        }),
        ('Winners & Payout', {
            'fields': (
                'num_perfect_picks',
                'payout_per_winner',
                'rollover_to_next',
            )
        }),
        ('Distribution Status', {
            'fields': (
                'is_distributed',
                'distributed_at',
                'distributed_by',
                'notes',
            )
        }),
        ('Statistics', {
            'fields': (
                'payment_count_display',
                'average_payment_display',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def week_display(self, obj):
        """Display week number with season year"""
        return f"Week {obj.week.week_number} ({obj.week.season_year})"
    week_display.short_description = 'Week'
    week_display.admin_order_field = 'week__week_number'

    def total_collected_display(self, obj):
        """Display total collected with formatting"""
        total_str = f'{obj.total_collected:.2f}'
        return format_html('<span style="color: green; font-weight: bold;">${}</span>', total_str)
    total_collected_display.short_description = 'Total Collected'
    total_collected_display.admin_order_field = 'total_collected'

    def weekly_pool_amount_display(self, obj):
        """Display weekly pool amount"""
        pool_str = f'{obj.weekly_pool_amount:.2f}'
        return format_html('<span style="color: blue; font-weight: bold;">${}</span>', pool_str)
    weekly_pool_amount_display.short_description = 'Pool Amount'
    weekly_pool_amount_display.admin_order_field = 'weekly_pool_amount'

    def company_fee_display(self, obj):
        """Display company fee"""
        fee_str = f'{obj.company_fee:.2f}'
        return format_html('<span style="color: orange;">${}</span>', fee_str)
    company_fee_display.short_description = 'Company Fee'
    company_fee_display.admin_order_field = 'company_fee'

    def payment_count_display(self, obj):
        """Count payments for this pool"""
        count = WeeklyPayment.objects.filter(
            team=obj.team,
            week=obj.week,
            payment_status='completed'
        ).count()
        return format_html(
            '<span style="font-weight: bold;">{} payments</span>',
            count
        )
    payment_count_display.short_description = 'Payment Count'

    def average_payment_display(self, obj):
        """Calculate average payment for this pool"""
        payments = WeeklyPayment.objects.filter(
            team=obj.team,
            week=obj.week,
            payment_status='completed'
        )
        count = payments.count()
        if count > 0:
            avg = obj.total_collected / count
            avg_str = f'{avg:.2f}'
            return format_html('${}', avg_str)
        return '-'
    average_payment_display.short_description = 'Avg Payment'

    def get_queryset(self, request):
        """Optimize queries with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('team', 'week')

    def changelist_view(self, request, extra_context=None):
        """Add prize pool statistics to the top of the list view"""
        extra_context = extra_context or {}

        # Calculate statistics
        pools = self.get_queryset(request)

        extra_context['total_pools'] = pools.count()
        extra_context['grand_total_collected'] = pools.aggregate(
            Sum('total_collected')
        )['total_collected__sum'] or 0
        extra_context['grand_total_pool'] = pools.aggregate(
            Sum('weekly_pool_amount')
        )['weekly_pool_amount__sum'] or 0
        extra_context['grand_total_fees'] = pools.aggregate(
            Sum('company_fee')
        )['company_fee__sum'] or 0

        return super().changelist_view(request, extra_context)

@admin.register(WeeklyPayout)
class WeeklyPayoutAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'team',
        'week',
        'amount_display',
        'payout_status',
        'payout_method',
        'payout_date',
    ]
    list_filter = [
        'payout_status',
        'payout_method',
        'team',
        'week',
    ]
    search_fields = [
        'user__username',
        'stripe_transfer_id',
        'paypal_payout_batch_id',
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Payout Info', {
            'fields': (
                'weekly_prize_pool',
                'user',
                'team',
                'week',
                'amount',
                'perfect_picks',
                'total_picks',
            )
        }),
        ('Status', {
            'fields': (
                'payout_status',
                'payout_method',
                'payout_date',
                'payout_initiated_at',
            )
        }),
        ('Stripe Info', {
            'fields': ('stripe_transfer_id',),
            'classes': ('collapse',)
        }),
        ('PayPal Info', {
            'fields': ('paypal_payout_batch_id',),
            'classes': ('collapse',)
        }),
        ('Other', {
            'fields': (
                'external_transaction_id',
                'last_payout_error',
                'retry_count',
                'processed_by',
                'notes',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        color = 'green' if obj.payout_status == 'paid' else 'orange'
        amount_str = f'{obj.amount:.2f}'
        return format_html(
            '<span style="color: {}; font-weight: bold;">${}</span>',
            color,
            amount_str
        )
    amount_display.short_description = 'Amount'

@admin.register(SeasonPot)
class SeasonPotAdmin(admin.ModelAdmin):
    list_display = [
        'team',
        'season_year',
        'total_accumulated_display',
        'first_place_display',
        'second_place_display',
        'third_place_display',
        'is_finalized',
        'is_distributed',
    ]
    list_filter = ['season_year', 'is_finalized', 'is_distributed']
    search_fields = ['team__name']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Season Info', {
            'fields': ('team', 'season_year', 'total_accumulated')
        }),
        ('Prize Distribution', {
            'fields': (
                'first_place_amount',
                'second_place_amount',
                'third_place_amount',
            )
        }),
        ('Winners', {
            'fields': (
                'first_place_user',
                'second_place_user',
                'third_place_user',
            )
        }),
        ('Status', {
            'fields': (
                'is_finalized',
                'is_distributed',
                'finalized_at',
                'distributed_at',
                'distributed_by',
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def total_accumulated_display(self, obj):
        total_str = f'{obj.total_accumulated:.2f}'
        return format_html('<span style="color: green; font-weight: bold;">${}</span>', total_str)
    total_accumulated_display.short_description = 'Total Pot'

    def first_place_display(self, obj):
        return f'${obj.first_place_amount:.2f} (50%)'
    first_place_display.short_description = '1st Place'

    def second_place_display(self, obj):
        return f'${obj.second_place_amount:.2f} (35%)'
    second_place_display.short_description = '2nd Place'

    def third_place_display(self, obj):
        return f'${obj.third_place_amount:.2f} (15%)'
    third_place_display.short_description = '3rd Place'


@admin.register(SeasonPayout)
class SeasonPayoutAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'team',
        'season_year',
        'placement_display',
        'total_points',
        'amount_display',
        'payout_status',
    ]
    list_filter = ['season_year', 'placement', 'payout_status']
    search_fields = ['user__username', 'team__name']
    readonly_fields = ['created_at', 'updated_at']

    def placement_display(self, obj):
        medals = {1: '🥇', 2: '🥈', 3: '🥉'}
        medal = medals.get(obj.placement, '')
        return f'{medal} {obj.placement}'
    placement_display.short_description = 'Place'

    def amount_display(self, obj):
        amount_str = f'{obj.amount:.2f}'
        return format_html(
            '<span style="color: green; font-weight: bold;">${}</span>',
            amount_str
        )
    amount_display.short_description = 'Prize'

@admin.register(CompanyFee)
class CompanyFeeAdmin(admin.ModelAdmin):
    list_display = [
        'team',
        'week',
        'fee_type',
        'amount_display',
        'payment_status',
        'collected_at',
    ]
    list_filter = ['fee_type', 'payment_status', 'team']
    search_fields = ['team__name']
    readonly_fields = ['created_at']

    def amount_display(self, obj):
        color = 'green' if obj.payment_status == 'collected' else 'orange'
        amount_str = f'{obj.amount:.2f}'
        return format_html(
            '<span style="color: {};">${}</span>',
            color,
            amount_str
        )
    amount_display.short_description = 'Fee'

# ==============================================================================
# PAYMENT MANAGEMENT
# ==============================================================================

# ==============================================================================
# PAYMENT MANAGEMENT - Add this section to admin.py
# Insert this after the CompanyFee section (around line 813)
# ==============================================================================

@admin.register(TeamStanding)
class TeamStandingAdmin(admin.ModelAdmin):
    list_display = [
        'team',
        'season_year',
        'total_team_points',
        'total_members',
        'active_members',
        'average_points_per_member_display',
        'participation_rate_display',
        'is_public',
        'rank',
    ]
    list_filter = ['season_year', 'is_public']
    search_fields = ['team__name']
    readonly_fields = ['updated_at']

    def average_points_per_member_display(self, obj):
        return f'{obj.average_points_per_member:.2f}'
    average_points_per_member_display.short_description = 'Avg Points'

    def participation_rate_display(self, obj):
        return f'{obj.participation_rate:.1f}%'
    participation_rate_display.short_description = 'Participation'


@admin.register(UserStanding)
class UserStandingAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'team',
        'season_year',
        'total_points',
        'accuracy_percentage_display',
        'perfect_weeks',
        'team_rank',
        'net_profit_display',
    ]
    list_filter = ['season_year', 'team']
    search_fields = ['user__username', 'team__name']
    readonly_fields = ['updated_at']

    fieldsets = (
        ('Standing Info', {
            'fields': ('user', 'team', 'season_year', 'team_rank')
        }),
        ('Performance', {
            'fields': (
                'total_points',
                'total_picks_made',
                'total_picks_hit',
                'accuracy_percentage',
                'weeks_participated',
                'perfect_weeks',
                'highest_weekly_score',
                'current_streak',
                'longest_streak',
            )
        }),
        ('Financial', {
            'fields': (
                'total_winnings',
                'total_paid',
                'net_profit',
            )
        }),
        ('Timestamps', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def accuracy_percentage_display(self, obj):
        color = 'green' if obj.accuracy_percentage >= 50 else 'orange'
        return format_html(
            '<span style="color: {};">{}%</span>',
            color,
            f'{obj.accuracy_percentage:.1f}'
        )
    accuracy_percentage_display.short_description = 'Accuracy'

    def net_profit_display(self, obj):
        color = 'green' if obj.net_profit >= 0 else 'red'
        return format_html(
            '<span style="color: {};">${}</span>',
            color,
            f'{obj.net_profit:.2f}'
        )
    net_profit_display.short_description = 'Profit/Loss'
