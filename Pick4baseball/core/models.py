"""
Baseball Pick 4 - Django Models
Complete data model for team-based pick'em game with payments

Created: January 22, 2026
Sprint: Sprint 2, Days 6-8
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils import timezone
from decimal import Decimal
import uuid


# ==============================================================================
# USER PROFILE
# ==============================================================================

class User(AbstractUser):
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

class UserProfile(models.Model):
    """Extended user information including payment preferences"""

    PAYOUT_METHOD_CHOICES = [
        ('balance', 'Keep in Account Balance'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('venmo', 'Venmo'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    timezone = models.CharField(
        max_length=50,
        default='America/Chicago',
        help_text='User timezone for deadline calculations'
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # Account balance system
    account_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Current account balance available for payments'
    )
    low_balance_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('15.00'),
        help_text='Alert user when balance drops below this amount'
    )
    low_balance_alert_sent = models.BooleanField(
        default=False,
        help_text='Has low balance alert been sent for current balance?'
    )
    last_low_balance_alert = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When was the last low balance alert sent?'
    )

    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True,
        help_text='Profile picture (max 5MB)'
    )

    # Payment info
    venmo_username = models.CharField(max_length=100, blank=True, null=True)
    paypal_email = models.EmailField(blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    preferred_payout_method = models.CharField(
        max_length=20,
        choices=PAYOUT_METHOD_CHOICES,
        default='manual'
    )

    # Lifetime statistics
    total_lifetime_winnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total amount won over all time (before payouts)'
    )
    total_lifetime_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Total amount paid in weekly fees over all time'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def net_profit(self):
        """Calculate lifetime profit/loss"""
        return self.total_lifetime_winnings - self.total_lifetime_paid

    @property
    def profile_picture_url(self):
        """Get profile picture URL or default avatar"""
        if self.profile_picture:
            return self.profile_picture.url
        return f'https://ui-avatars.com/api/?name={self.user.username}&size=150&background=667eea&color=fff'


class AccountTransaction(models.Model):
    """
    Complete audit trail of all account balance changes.
    Tracks deposits (winnings), withdrawals, and payments.
    """

    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),           # Winnings added to balance
        ('withdrawal', 'Withdrawal'),     # User withdrew funds
        ('payment', 'Payment'),           # Paid weekly fee from balance
        ('refund', 'Refund'),             # Payment refunded to balance
        ('adjustment', 'Admin Adjustment'), # Manual admin adjustment
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='account_transactions'
    )

    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    balance_before = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='completed'
    )

    # Context
    description = models.CharField(
        max_length=200,
        help_text='Human-readable description'
    )
    related_payment = models.ForeignKey(
        'WeeklyPayment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    related_payout = models.ForeignKey(
        'WeeklyPayout',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )

    # External references (for withdrawals)
    stripe_transfer_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    venmo_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    # Admin tracking
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_transactions',
        help_text='Admin who processed this transaction (if applicable)'
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'account_transactions'
        verbose_name = 'Account Transaction'
        verbose_name_plural = 'Account Transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['related_payment']),
            models.Index(fields=['related_payout']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ${self.amount} ({self.created_at.strftime('%Y-%m-%d')})"

# ==============================================================================
# TEAM MANAGEMENT
# ==============================================================================

class Team(models.Model):
    """Independent team/league with its own settings and prize pools"""

    WEEKLY_FEE_CHOICES = [
        (Decimal('5.00'), '$5 per week'),
        (Decimal('10.00'), '$10 per week'),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)

    captain = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='captained_teams',
        help_text='Team admin/creator'
    )

    weekly_fee = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        choices=WEEKLY_FEE_CHOICES,
        help_text='Weekly entry fee per player'
    )

    season_year = models.IntegerField(
        help_text='Which MLB season this team plays in'
    )

    # Settings
    is_public = models.BooleanField(
        default=False,
        help_text='Show team on public leaderboards'
    )
    is_active = models.BooleanField(default=True)

    min_members = models.IntegerField(
        default=3,
        validators=[MinValueValidator(3)],
        help_text='Minimum 3 members required'
    )
    max_members = models.IntegerField(
        blank=True,
        null=True,
        help_text='Optional member limit'
    )

    join_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text='Secret code for players to join'
    )

    # Payment integration
    stripe_connected_account_id = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    paypal_email = models.EmailField(blank=True, null=True)
    auto_payout_enabled = models.BooleanField(
        default=False,
        help_text='Enable automated payouts via Stripe/PayPal'
    )

    logo_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teams'
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
        ordering = ['-season_year', 'name']
        indexes = [
            models.Index(fields=['captain']),
            models.Index(fields=['season_year']),
            models.Index(fields=['season_year', 'is_public']),
            models.Index(fields=['join_code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.season_year})"

    def save(self, *args, **kwargs):
        # Auto-generate slug
        if not self.slug:
            self.slug = slugify(self.name)

        # Auto-generate join code
        if not self.join_code:
            self.join_code = str(uuid.uuid4())[:8].upper()

        super().save(*args, **kwargs)

    @property
    def member_count(self):
        """Get current active member count"""
        return self.members.filter(status='active').count()

    @property
    def is_ready(self):
        """Check if team meets minimum member requirement"""
        return self.member_count >= self.min_members


class TeamMember(models.Model):
    """User membership in a team"""

    ROLE_CHOICES = [
        ('captain', 'Captain'),
        ('co_captain', 'Co-Captain'),
        ('member', 'Member'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('removed', 'Removed'),
    ]

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(blank=True, null=True)
    removed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='removed_members'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_members'
        verbose_name = 'Team Member'
        verbose_name_plural = 'Team Members'
        unique_together = [('team', 'user', 'status')]
        indexes = [
            models.Index(fields=['team', 'status']),
            models.Index(fields=['user']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.role})"


class TeamInvitation(models.Model):
    """Invitations to join teams"""

    TYPE_CHOICES = [
        ('invite', 'Captain Invite'),
        ('request', 'Join Request'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    invited_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )

    invited_user_email = models.EmailField()
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_invitations'
    )

    invitation_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='invite'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    token = models.CharField(max_length=64, unique=True, blank=True)
    message = models.TextField(blank=True)

    expires_at = models.DateTimeField()
    responded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'team_invitations'
        verbose_name = 'Team Invitation'
        verbose_name_plural = 'Team Invitations'
        unique_together = [('team', 'invited_user_email', 'status')]
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['team', 'status']),
        ]

    def __str__(self):
        return f"{self.invitation_type}: {self.invited_user_email} → {self.team.name}"

    def save(self, *args, **kwargs):
        # Auto-generate token
        if not self.token:
            self.token = str(uuid.uuid4())

        # Auto-set expiration (7 days)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at


# ==============================================================================
# GAME CORE
# ==============================================================================

class Week(models.Model):
    """Game weeks - Saturdays during MLB season"""

    week_number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(26)]
    )
    season_year = models.IntegerField()

    saturday_date = models.DateField(help_text='The specific Saturday for this week')
    deadline_utc = models.DateTimeField(help_text='Deadline in UTC (11 AM CST = 5 PM UTC)')

    is_active = models.BooleanField(
        default=False,
        help_text='Only one week should be active at a time'
    )
    is_completed = models.BooleanField(default=False)

    games_start_time = models.DateTimeField(null=True, blank=True)
    games_end_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'weeks'
        verbose_name = 'Week'
        verbose_name_plural = 'Weeks'
        unique_together = [('week_number', 'season_year')]
        ordering = ['season_year', 'week_number']
        indexes = [
            models.Index(fields=['season_year', 'week_number']),
            models.Index(fields=['is_active']),
            models.Index(fields=['saturday_date']),
        ]

    def __str__(self):
        return f"Week {self.week_number}, {self.season_year} ({self.saturday_date})"

    @property
    def is_past_deadline(self):
        """Check if deadline has passed"""
        return timezone.now() > self.deadline_utc


class MLBPlayer(models.Model):
    """MLB players from Stats API"""

    mlb_player_id = models.IntegerField(unique=True)

    full_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)

    team_name = models.CharField(max_length=50)
    team_abbreviation = models.CharField(max_length=10)
    position = models.CharField(max_length=10)

    is_active = models.BooleanField(default=True)
    is_pitcher = models.BooleanField(default=False)
    is_two_way_player = models.BooleanField(
        default=False,
        help_text='Players like Ohtani who pitch and bat'
    )

    mlb_team_id = models.IntegerField(null=True, blank=True)
    jersey_number = models.IntegerField(null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mlb_players'
        verbose_name = 'MLB Player'
        verbose_name_plural = 'MLB Players'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['mlb_player_id']),
            models.Index(fields=['team_abbreviation']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_pitcher', 'is_active']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.team_abbreviation})"


class PickCategory(models.Model):
    """The 4 pick categories"""

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField()

    requires_pitcher = models.BooleanField(
        default=False,
        help_text='True for SWP and S, False for 2H and HR'
    )

    display_order = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'pick_categories'
        verbose_name = 'Pick Category'
        verbose_name_plural = 'Pick Categories'
        ordering = ['display_order']

    def __str__(self):
        return f"{self.code} - {self.name}"


class Pick(models.Model):
    """User's weekly picks"""

    RESULT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('hit', 'Hit'),
        ('miss', 'Miss'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='picks'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='picks'
    )
    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name='picks'
    )
    category = models.ForeignKey(
        PickCategory,
        on_delete=models.CASCADE,
        related_name='picks'
    )
    player = models.ForeignKey(
        MLBPlayer,
        on_delete=models.CASCADE,
        related_name='picks'
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

    # Cross-team pick copying
    copied_from_team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='copied_picks'
    )
    is_auto_copied = models.BooleanField(default=False)

    # Scoring
    points_earned = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    result_status = models.CharField(
        max_length=20,
        choices=RESULT_STATUS_CHOICES,
        default='pending'
    )
    scored_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'picks'
        verbose_name = 'Pick'
        verbose_name_plural = 'Picks'
        unique_together = [('user', 'team', 'week', 'category')]
        indexes = [
            models.Index(fields=['user', 'week']),
            models.Index(fields=['week', 'result_status']),
            models.Index(fields=['player', 'week']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.user.username} - Week {self.week.week_number} - {self.category.code}: {self.player.full_name}"


class WeeklyResult(models.Model):
    """Actual game outcomes - source of truth for scoring"""

    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name='results'
    )
    player = models.ForeignKey(
        MLBPlayer,
        on_delete=models.CASCADE,
        related_name='results'
    )
    category = models.ForeignKey(
        PickCategory,
        on_delete=models.CASCADE,
        related_name='results'
    )

    achieved = models.BooleanField(
        default=False,
        help_text='Did player achieve this stat?'
    )
    stat_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Actual stat value'
    )

    game_date = models.DateField()
    game_id = models.CharField(max_length=50, blank=True, null=True)
    opponent_team = models.CharField(max_length=50, blank=True, null=True)

    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_results'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'weekly_results'
        verbose_name = 'Weekly Result'
        verbose_name_plural = 'Weekly Results'
        unique_together = [('week', 'player', 'category')]
        indexes = [
            models.Index(fields=['week', 'achieved']),
            models.Index(fields=['player', 'week']),
            models.Index(fields=['category', 'week', 'achieved']),
        ]

    def __str__(self):
        status = "✓" if self.achieved else "✗"
        return f"{status} Week {self.week.week_number} - {self.player.full_name} - {self.category.code}"


# ==============================================================================
# FINANCIAL - PAYMENTS & PRIZES
# ==============================================================================

class WeeklyPayment(models.Model):
    """Track weekly payments from players"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('venmo', 'Venmo'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='weekly_payments'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='weekly_payments'
    )
    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=6, decimal_places=2)
    payment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='stripe'
    )

    # Payment processor IDs
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    external_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    payment_date = models.DateTimeField(null=True, blank=True)
    last_payment_error = models.TextField(blank=True, null=True)

    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_payments'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'weekly_payments'
        verbose_name = 'Weekly Payment'
        verbose_name_plural = 'Weekly Payments'
        unique_together = [('user', 'team', 'week')]
        indexes = [
            models.Index(fields=['team', 'week', 'payment_status']),
            models.Index(fields=['user', 'payment_status']),
            models.Index(fields=['stripe_payment_intent_id']),
            models.Index(fields=['paypal_transaction_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - Week {self.week.week_number} - ${self.amount} ({self.payment_status})"


class WeeklyPrizePool(models.Model):
    """Team's weekly prize pool with rollover logic"""

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='weekly_prize_pools'
    )
    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name='prize_pools'
    )

    # Money breakdown
    total_collected = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    rollover_from_previous = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Amount rolled over from previous week'
    )
    weekly_pool_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='80% of collections + rollover'
    )
    season_pot_contribution = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='10% of new collections'
    )
    company_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='10% of new collections'
    )

    per_pick_value = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )

    # Winners
    num_perfect_picks = models.IntegerField(default=0)
    payout_per_winner = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    rollover_to_next = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Amount rolling to next week if no winners'
    )

    is_distributed = models.BooleanField(default=False)
    distributed_at = models.DateTimeField(null=True, blank=True)
    distributed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='distributed_pools'
    )

    # Scoring tracking (ADD THESE HERE, NOT AT THE TOP)
    is_scored = models.BooleanField(
        default=False,
        help_text='Has this week been scored?'
    )
    scored_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When picks were scored'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'weekly_prize_pools'
        verbose_name = 'Weekly Prize Pool'
        verbose_name_plural = 'Weekly Prize Pools'
        unique_together = [('team', 'week')]

    def __str__(self):
        return f"{self.team.name} - Week {self.week.week_number} - Pool: ${self.weekly_pool_amount}"

    @property
    def payment_count(self):
        """Count of completed payments for this team/week"""
        return self.team.weekly_payments.filter(
            week=self.week,
            payment_status='completed'
        ).count()

    @property
    def average_payment(self):
        """Calculate average payment amount for this week"""
        if self.payment_count > 0:
            return self.total_collected / Decimal(str(self.payment_count))
        return Decimal('0.00')

class WeeklyPayout(models.Model):
    """Weekly prize payouts to winners"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('manual', 'Manual'),
    ]

    METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('venmo', 'Venmo'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]

    weekly_prize_pool = models.ForeignKey(
        WeeklyPrizePool,
        on_delete=models.CASCADE,
        related_name='payouts'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='weekly_payouts'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='weekly_payouts'
    )
    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        related_name='payouts'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    perfect_picks = models.IntegerField(default=4)
    total_picks = models.IntegerField(default=4)

    payout_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payout_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='stripe'
    )

    # Payout processor IDs
    stripe_transfer_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_payout_batch_id = models.CharField(max_length=100, blank=True, null=True)
    external_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    payout_date = models.DateTimeField(null=True, blank=True)
    payout_initiated_at = models.DateTimeField(null=True, blank=True)
    last_payout_error = models.TextField(blank=True, null=True)
    retry_count = models.IntegerField(default=0)

    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_payouts'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'weekly_payouts'
        verbose_name = 'Weekly Payout'
        verbose_name_plural = 'Weekly Payouts'
        indexes = [
            models.Index(fields=['user', 'week']),
            models.Index(fields=['team', 'week']),
            models.Index(fields=['payout_status']),
        ]

    def __str__(self):
        return f"{self.user.username} - Week {self.week.week_number} - ${self.amount} ({self.payout_status})"


class SeasonPot(models.Model):
    """Team's accumulated season championship pot"""

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='season_pots'
    )
    season_year = models.IntegerField()

    total_accumulated = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Prize distribution (50%/35%/15%)
    first_place_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    second_place_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    third_place_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    # Winners
    first_place_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='first_place_seasons'
    )
    second_place_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='second_place_seasons'
    )
    third_place_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='third_place_seasons'
    )

    is_finalized = models.BooleanField(default=False)
    is_distributed = models.BooleanField(default=False)
    finalized_at = models.DateTimeField(null=True, blank=True)
    distributed_at = models.DateTimeField(null=True, blank=True)
    distributed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='distributed_season_pots'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'season_pots'
        verbose_name = 'Season Pot'
        verbose_name_plural = 'Season Pots'
        unique_together = [('team', 'season_year')]

    def __str__(self):
        return f"{self.team.name} - {self.season_year} - Pot: ${self.total_accumulated}"

    def calculate_prizes(self):
        """Calculate 50%/35%/15% split"""
        self.first_place_amount = self.total_accumulated * Decimal('0.50')
        self.second_place_amount = self.total_accumulated * Decimal('0.35')
        self.third_place_amount = self.total_accumulated * Decimal('0.15')
        self.save()


class SeasonPayout(models.Model):
    """Season championship payouts"""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    METHOD_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('venmo', 'Venmo'),
        ('cash', 'Cash'),
        ('other', 'Other'),
    ]

    season_pot = models.ForeignKey(
        SeasonPot,
        on_delete=models.CASCADE,
        related_name='payouts'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='season_payouts'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='season_payouts'
    )
    season_year = models.IntegerField()

    placement = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)]
    )
    total_points = models.IntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='50, 35, or 15'
    )

    payout_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payout_method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        default='stripe'
    )

    # Payout processor IDs
    stripe_transfer_id = models.CharField(max_length=100, blank=True, null=True)
    paypal_payout_batch_id = models.CharField(max_length=100, blank=True, null=True)
    external_transaction_id = models.CharField(max_length=100, blank=True, null=True)

    payout_date = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_season_payouts'
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'season_payouts'
        verbose_name = 'Season Payout'
        verbose_name_plural = 'Season Payouts'

    def __str__(self):
        return f"{self.user.username} - {self.season_year} - {self.placement} place - ${self.amount}"


class CompanyFee(models.Model):
    """Fees owed to Heald & Heritage LLC"""

    TYPE_CHOICES = [
        ('weekly', 'Weekly'),
        ('season', 'Season'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('collected', 'Collected'),
        ('waived', 'Waived'),
    ]

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='company_fees'
    )
    week = models.ForeignKey(
        Week,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='company_fees'
    )

    fee_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    collected_from = models.CharField(
        max_length=50,
        default='weekly_pool',
        help_text='weekly_pool or season_pot'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    collected_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'company_fees'
        verbose_name = 'Company Fee'
        verbose_name_plural = 'Company Fees'

    def __str__(self):
        week_str = f"Week {self.week.week_number}" if self.week else "Season"
        return f"{self.team.name} - {week_str} - ${self.amount}"


# ==============================================================================
# LEADERBOARDS & STANDINGS
# ==============================================================================

class TeamStanding(models.Model):
    """Team-level statistics for leaderboards"""

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='standings'
    )
    season_year = models.IntegerField()

    total_members = models.IntegerField(default=0)
    active_members = models.IntegerField(default=0)

    total_team_points = models.IntegerField(default=0)
    average_points_per_member = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00')
    )

    total_perfect_weeks = models.IntegerField(default=0)
    participation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='% of members who play each week'
    )

    is_public = models.BooleanField(default=False)
    rank = models.IntegerField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'team_standings'
        verbose_name = 'Team Standing'
        verbose_name_plural = 'Team Standings'
        unique_together = [('team', 'season_year')]
        indexes = [
            models.Index(fields=['season_year', 'total_team_points']),
        ]

    def __str__(self):
        return f"{self.team.name} - {self.season_year} - {self.total_team_points} pts"


class UserStanding(models.Model):
    """User statistics per team"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='standings'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='user_standings'
    )
    season_year = models.IntegerField()

    # Performance stats
    total_points = models.IntegerField(default=0)
    total_picks_made = models.IntegerField(default=0)
    total_picks_hit = models.IntegerField(default=0)
    accuracy_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )

    weeks_participated = models.IntegerField(default=0)
    perfect_weeks = models.IntegerField(default=0)
    highest_weekly_score = models.IntegerField(default=0)

    current_streak = models.IntegerField(
        default=0,
        help_text='Consecutive weeks with at least 1 hit'
    )
    longest_streak = models.IntegerField(default=0)

    team_rank = models.IntegerField(null=True, blank=True)

    # Financial
    total_winnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    net_profit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_standings'
        verbose_name = 'User Standing'
        verbose_name_plural = 'User Standings'
        unique_together = [('user', 'team', 'season_year')]
        indexes = [
            models.Index(fields=['team', 'season_year', 'total_points']),
            models.Index(fields=['season_year', 'total_points']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.team.name} - {self.total_points} pts"

    def update_accuracy(self):
        """Calculate accuracy percentage"""
        if self.total_picks_made > 0:
            self.accuracy_percentage = (
                Decimal(self.total_picks_hit) / Decimal(self.total_picks_made) * Decimal('100.00')
            )
        else:
            self.accuracy_percentage = Decimal('0.00')

        self.net_profit = self.total_winnings - self.total_paid
        self.save()
