import math
from datetime import date

from django.db.models import Max
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Customer, Loan
from .serializers import (
    RegisterSerializer,
    CheckEligibilitySerializer,
    CreateLoanSerializer,
)


def calculate_credit_score(customer):
    """
    Calculate credit score (out of 100) based on historical loan data.
    Components:
        i.   Past loans paid on time
        ii.  Number of loans taken in past
        iii. Loan activity in current year
        iv.  Loan approved volume
        v.   If sum of current loans > approved limit => score = 0
    """
    loans = Loan.objects.filter(customer=customer)

    if not loans.exists():
        return 50  # Default score for customers with no loan history

    total_loans = loans.count()
    current_year = date.today().year
    current_year_loans = loans.filter(start_date__year=current_year).count()

    # Past loans paid on time
    total_emis = 0
    emis_on_time = 0
    for loan in loans:
        if loan.tenure > 0:
            total_emis += loan.tenure
            emis_on_time += loan.emis_paid_on_time

    on_time_ratio = emis_on_time / total_emis if total_emis > 0 else 0

    # Loan approved volume
    total_loan_volume = sum(loan.loan_amount for loan in loans)

    # Sum of current loans (active loans where end_date is in the future)
    today = date.today()
    current_loans = loans.filter(end_date__gte=today)
    sum_current_loans = sum(loan.loan_amount for loan in current_loans)

    # If sum of current loans > approved limit, credit score = 0
    if sum_current_loans > customer.approved_limit:
        return 0

    # Calculate composite credit score
    score = 0

    # Component i: Past loans paid on time (max 30 points)
    score += on_time_ratio * 30

    # Component ii: Number of loans (moderate number is good, max 20 points)
    if total_loans <= 5:
        score += 20
    elif total_loans <= 10:
        score += 15
    elif total_loans <= 15:
        score += 10
    else:
        score += 5

    # Component iii: Loan activity in current year (max 20 points)
    if current_year_loans == 0:
        score += 20
    elif current_year_loans <= 2:
        score += 15
    elif current_year_loans <= 4:
        score += 10
    else:
        score += 5

    # Component iv: Loan approved volume (max 30 points)
    if customer.approved_limit > 0:
        volume_ratio = total_loan_volume / customer.approved_limit
        if volume_ratio <= 0.3:
            score += 30
        elif volume_ratio <= 0.5:
            score += 25
        elif volume_ratio <= 0.7:
            score += 20
        elif volume_ratio <= 1.0:
            score += 10
        else:
            score += 0

    return min(round(score), 100)


def calculate_monthly_installment(loan_amount, interest_rate, tenure):
    """
    Calculate EMI using compound interest formula:
    EMI = P * r * (1+r)^n / ((1+r)^n - 1)
    where r = monthly interest rate, n = tenure in months
    """
    if interest_rate == 0:
        return round(loan_amount / tenure, 2) if tenure > 0 else 0

    monthly_rate = interest_rate / (12 * 100)
    if monthly_rate == 0:
        return round(loan_amount / tenure, 2) if tenure > 0 else 0

    emi = loan_amount * monthly_rate * math.pow(1 + monthly_rate, tenure) / \
          (math.pow(1 + monthly_rate, tenure) - 1)
    return round(emi, 2)


@api_view(['POST'])
def register(request):
    """
    /api/register
    Add a new customer with approved_limit = 36 * monthly_salary
    (rounded to nearest lakh).
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    monthly_income = data['monthly_income']

    # approved_limit = 36 * monthly_salary, rounded to nearest lakh (100000)
    approved_limit = round(36 * monthly_income / 100000) * 100000

    # Generate next customer_id
    max_id = Customer.objects.aggregate(max_id=Max('customer_id'))['max_id']
    next_id = (max_id or 0) + 1

    customer = Customer.objects.create(
        customer_id=next_id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        age=data.get('age'),
        phone_number=str(data['phone_number']),
        monthly_salary=monthly_income,
        approved_limit=approved_limit,
    )

    response_data = {
        'customer_id': customer.customer_id,
        'name': f"{customer.first_name} {customer.last_name}",
        'age': customer.age,
        'monthly_income': customer.monthly_salary,
        'approved_limit': customer.approved_limit,
        'phone_number': customer.phone_number,
    }

    return Response(response_data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def check_eligibility(request):
    """
    /api/check-eligibility
    Check loan eligibility based on credit score.
    """
    serializer = CheckEligibilitySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    customer_id = data['customer_id']
    loan_amount = data['loan_amount']
    interest_rate = data['interest_rate']
    tenure = data['tenure']

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    credit_score = calculate_credit_score(customer)

    # Check if sum of current EMIs > 50% of monthly salary
    today = date.today()
    current_loans = Loan.objects.filter(customer=customer, end_date__gte=today)
    sum_current_emis = sum(loan.monthly_repayment for loan in current_loans)

    approval = False
    corrected_interest_rate = interest_rate

    if sum_current_emis > 0.5 * customer.monthly_salary:
        approval = False
    elif credit_score > 50:
        approval = True
    elif credit_score > 30:
        if interest_rate >= 12:
            approval = True
        else:
            corrected_interest_rate = 12
            approval = True
    elif credit_score > 10:
        if interest_rate >= 16:
            approval = True
        else:
            corrected_interest_rate = 16
            approval = True
    else:
        approval = False

    monthly_installment = calculate_monthly_installment(
        loan_amount, corrected_interest_rate, tenure
    )

    response_data = {
        'customer_id': customer_id,
        'approval': approval,
        'interest_rate': interest_rate,
        'corrected_interest_rate': corrected_interest_rate,
        'tenure': tenure,
        'monthly_installment': monthly_installment,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_loan(request):
    """
    /api/create-loan
    Process a new loan based on eligibility.
    """
    serializer = CreateLoanSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    customer_id = data['customer_id']
    loan_amount = data['loan_amount']
    interest_rate = data['interest_rate']
    tenure = data['tenure']

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    credit_score = calculate_credit_score(customer)

    # Check eligibility
    today = date.today()
    current_loans = Loan.objects.filter(customer=customer, end_date__gte=today)
    sum_current_emis = sum(loan.monthly_repayment for loan in current_loans)

    approval = False
    corrected_interest_rate = interest_rate
    message = ''

    if sum_current_emis > 0.5 * customer.monthly_salary:
        approval = False
        message = 'Loan not approved: sum of current EMIs exceeds 50% of monthly salary'
    elif credit_score > 50:
        approval = True
        message = 'Loan approved'
    elif credit_score > 30:
        if interest_rate >= 12:
            approval = True
            message = 'Loan approved'
        else:
            corrected_interest_rate = 12
            approval = True
            message = 'Loan approved with corrected interest rate'
    elif credit_score > 10:
        if interest_rate >= 16:
            approval = True
            message = 'Loan approved'
        else:
            corrected_interest_rate = 16
            approval = True
            message = 'Loan approved with corrected interest rate'
    else:
        approval = False
        message = 'Loan not approved: credit score too low'

    loan_id = None
    monthly_installment = None

    if approval:
        monthly_installment = calculate_monthly_installment(
            loan_amount, corrected_interest_rate, tenure
        )

        from dateutil.relativedelta import relativedelta
        start_date = today
        end_date = today + relativedelta(months=tenure)

        # Generate next loan_id
        max_loan_id = Loan.objects.aggregate(max_id=Max('loan_id'))['max_id']
        next_loan_id = (max_loan_id or 0) + 1

        loan = Loan.objects.create(
            loan_id=next_loan_id,
            customer=customer,
            loan_amount=loan_amount,
            tenure=tenure,
            interest_rate=corrected_interest_rate,
            monthly_repayment=monthly_installment,
            emis_paid_on_time=0,
            start_date=start_date,
            end_date=end_date,
        )
        loan_id = loan.loan_id

        # Update customer current debt
        customer.current_debt += loan_amount
        customer.save()

    response_data = {
        'loan_id': loan_id,
        'customer_id': customer_id,
        'loan_approved': approval,
        'message': message,
        'monthly_installment': monthly_installment,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
def view_loan(request, loan_id):
    """
    /api/view-loan/<loan_id>
    View loan details and customer details.
    """
    try:
        loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
    except Loan.DoesNotExist:
        return Response(
            {'error': 'Loan not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    customer = loan.customer
    response_data = {
        'loan_id': loan.loan_id,
        'customer': {
            'id': customer.customer_id,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'phone_number': customer.phone_number,
            'age': customer.age,
        },
        'loan_amount': loan.loan_amount,
        'interest_rate': loan.interest_rate,
        'monthly_installment': loan.monthly_repayment,
        'tenure': loan.tenure,
    }

    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['GET'])
def view_loans(request, customer_id):
    """
    /api/view-loans/<customer_id>
    View all current loan details by customer ID.
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response(
            {'error': 'Customer not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    loans = Loan.objects.filter(customer=customer)

    loan_items = []
    for loan in loans:
        repayments_left = max(0, loan.tenure - loan.emis_paid_on_time)
        loan_items.append({
            'loan_id': loan.loan_id,
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_repayment,
            'repayments_left': repayments_left,
        })

    return Response(loan_items, status=status.HTTP_200_OK)
