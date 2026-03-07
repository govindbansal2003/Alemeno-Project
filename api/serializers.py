from rest_framework import serializers

class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(required=False)
    monthly_income = serializers.IntegerField()
    phone_number = serializers.IntegerField()

class RegisterResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    name = serializers.CharField()
    age = serializers.IntegerField()
    monthly_income = serializers.IntegerField()
    approved_limit = serializers.IntegerField()
    phone_number = serializers.IntegerField()

class CheckEligibilitySerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()

class CheckEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()

class CreateLoanSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()

class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.FloatField(allow_null=True)

class CustomerDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='customer_id')
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.IntegerField()
    age = serializers.IntegerField()

class ViewLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField()
    customer = CustomerDetailSerializer()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    monthly_installment = serializers.FloatField()
    tenure = serializers.IntegerField()

class ViewLoansItemSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()
    interest_rate = serializers.FloatField()
    monthly_installment = serializers.FloatField()
    repayments_left = serializers.IntegerField()