"""Authorize.Net client adapter"""
from authorizenet import apicontractsv1, constants
from authorizenet.apicontrollers import createTransactionController, ARBCreateSubscriptionController

from app.core.config import settings
from app.adapters.authorize_net.models import (
    PurchaseRequest,
    TransactionResponse,
    CaptureRequest,
    VoidRequest,
    RefundRequest,
    SubscriptionRequest,
    SubscriptionResponse,
)
from app.adapters.authorize_net.exceptions import (
    AuthorizeNetAPIError,
    AuthorizeNetConnectionError,
    AuthorizeNetValidationError,
)
import structlog

logger = structlog.get_logger()


class AuthorizeNetClient:
    """Client wrapper for Authorize.Net API"""

    def __init__(self):
        """Initialize the client with credentials from settings"""
        self.api_login_id = settings.AUTHORIZE_NET_API_LOGIN_ID
        self.transaction_key = settings.AUTHORIZE_NET_TRANSACTION_KEY
        self.environment = settings.AUTHORIZE_NET_ENVIRONMENT
        self.max_ref_id_length = 20

    def _create_merchant_auth(self):
        """Create merchant authentication object"""
        merchant_auth = apicontractsv1.merchantAuthenticationType()
        merchant_auth.name = self.api_login_id
        merchant_auth.transactionKey = self.transaction_key
        return merchant_auth

    def _get_environment(self):
        """Map configured environment to Authorize.Net constant"""
        env = (self.environment or "").lower()
        env_map = {
            "sandbox": constants.constants.SANDBOX,
            "production": constants.constants.PRODUCTION,
        }
        if env not in env_map:
            raise AuthorizeNetValidationError(
                f"Unsupported Authorize.Net environment: {self.environment}"
            )
        return env_map[env]

    def _sanitize_ref_id(self, ref_id: str | None) -> str | None:
        """Ensure refId meets Authorize.Net length constraints (max 20)"""
        if not ref_id:
            return None
        if len(ref_id) > self.max_ref_id_length:
            logger.warning(
                "Truncating refId to meet Authorize.Net length constraint",
                ref_id=ref_id,
                max_length=self.max_ref_id_length,
            )
        return ref_id[: self.max_ref_id_length]

    def purchase(self, request: PurchaseRequest) -> TransactionResponse:
        """Process a purchase transaction (auth + capture)"""
        try:
            # Create merchant authentication
            merchant_auth = self._create_merchant_auth()

            # Create credit card payment
            credit_card = apicontractsv1.creditCardType()
            credit_card.cardNumber = request.credit_card.card_number.replace(" ", "").replace("-", "")
            # Convert expiration date format (YYYY-MM or MM/YY) to MM/YY
            exp_date = request.credit_card.expiration_date
            if len(exp_date) == 7 and "-" in exp_date:  # YYYY-MM format
                year, month = exp_date.split("-")
                exp_date = f"{month}/{year[-2:]}"  # Convert to MM/YY
            credit_card.expirationDate = exp_date
            if request.credit_card.card_code:
                credit_card.cardCode = request.credit_card.card_code

            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card

            # Create order information
            order = apicontractsv1.orderType()
            if request.invoice_number:
                order.invoiceNumber = request.invoice_number
            if request.description:
                order.description = request.description

            # Create customer address
            customer_address = apicontractsv1.customerAddressType()
            customer_address.firstName = request.customer_address.first_name
            customer_address.lastName = request.customer_address.last_name
            if request.customer_address.company:
                customer_address.company = request.customer_address.company
            customer_address.address = request.customer_address.address
            customer_address.city = request.customer_address.city
            customer_address.state = request.customer_address.state
            customer_address.zip = request.customer_address.zip
            customer_address.country = request.customer_address.country

            # Create customer data
            customer_data = apicontractsv1.customerDataType()
            customer_data.type = request.customer_data.customer_type
            customer_data.id = request.customer_data.customer_id
            customer_data.email = request.customer_data.email

            # Create transaction settings
            duplicate_window_setting = apicontractsv1.settingType()
            duplicate_window_setting.settingName = "duplicateWindow"
            duplicate_window_setting.settingValue = str(request.duplicate_window)
            settings_array = apicontractsv1.ArrayOfSetting()
            settings_array.setting.append(duplicate_window_setting)

            # Create line items if provided
            line_items = None
            if request.line_items:
                line_items = apicontractsv1.ArrayOfLineItem()
                for item in request.line_items:
                    line_item = apicontractsv1.lineItemType()
                    line_item.itemId = item.item_id
                    line_item.name = item.name
                    line_item.description = item.description
                    line_item.quantity = item.quantity
                    line_item.unitPrice = item.unit_price
                    line_items.lineItem.append(line_item)

            # Create transaction request
            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "authCaptureTransaction"
            transaction_request.amount = str(request.amount)
            transaction_request.payment = payment
            transaction_request.order = order
            transaction_request.billTo = customer_address
            transaction_request.customer = customer_data
            transaction_request.transactionSettings = settings_array
            if line_items:
                transaction_request.lineItems = line_items

            # Create complete transaction request
            create_transaction_request = apicontractsv1.createTransactionRequest()
            create_transaction_request.merchantAuthentication = merchant_auth
            sanitized_ref = self._sanitize_ref_id(request.ref_id)
            if sanitized_ref:
                create_transaction_request.refId = sanitized_ref
            create_transaction_request.transactionRequest = transaction_request

            # Execute transaction
            controller = createTransactionController(create_transaction_request)
            controller.setenvironment(self._get_environment())
            controller.execute()

            # Get response
            response = controller.getresponse()

            return self._parse_response(response)

        except AuthorizeNetValidationError:
            raise
        except Exception as e:
            logger.error("Authorize.Net API error", error=str(e), exc_info=True)
            raise AuthorizeNetConnectionError(f"Failed to connect to Authorize.Net: {str(e)}")

    def authorize(self, request: PurchaseRequest) -> TransactionResponse:
        """Authorize a transaction without capturing"""
        try:
            merchant_auth = self._create_merchant_auth()

            credit_card = apicontractsv1.creditCardType()
            credit_card.cardNumber = request.credit_card.card_number.replace(" ", "").replace("-", "")
            exp_date = request.credit_card.expiration_date
            if len(exp_date) == 7 and "-" in exp_date:
                year, month = exp_date.split("-")
                exp_date = f"{month}/{year[-2:]}"
            credit_card.expirationDate = exp_date
            if request.credit_card.card_code:
                credit_card.cardCode = request.credit_card.card_code

            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card

            order = apicontractsv1.orderType()
            if request.invoice_number:
                order.invoiceNumber = request.invoice_number
            if request.description:
                order.description = request.description

            customer_address = apicontractsv1.customerAddressType()
            customer_address.firstName = request.customer_address.first_name
            customer_address.lastName = request.customer_address.last_name
            if request.customer_address.company:
                customer_address.company = request.customer_address.company
            customer_address.address = request.customer_address.address
            customer_address.city = request.customer_address.city
            customer_address.state = request.customer_address.state
            customer_address.zip = request.customer_address.zip
            customer_address.country = request.customer_address.country

            customer_data = apicontractsv1.customerDataType()
            customer_data.type = request.customer_data.customer_type
            customer_data.id = request.customer_data.customer_id
            customer_data.email = request.customer_data.email

            duplicate_window_setting = apicontractsv1.settingType()
            duplicate_window_setting.settingName = "duplicateWindow"
            duplicate_window_setting.settingValue = str(request.duplicate_window)
            settings_array = apicontractsv1.ArrayOfSetting()
            settings_array.setting.append(duplicate_window_setting)

            line_items = None
            if request.line_items:
                line_items = apicontractsv1.ArrayOfLineItem()
                for item in request.line_items:
                    line_item = apicontractsv1.lineItemType()
                    line_item.itemId = item.item_id
                    line_item.name = item.name
                    line_item.description = item.description
                    line_item.quantity = item.quantity
                    line_item.unitPrice = item.unit_price
                    line_items.lineItem.append(line_item)

            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "authOnlyTransaction"
            transaction_request.amount = str(request.amount)
            transaction_request.payment = payment
            transaction_request.order = order
            transaction_request.billTo = customer_address
            transaction_request.customer = customer_data
            transaction_request.transactionSettings = settings_array
            if line_items:
                transaction_request.lineItems = line_items

            create_transaction_request = apicontractsv1.createTransactionRequest()
            create_transaction_request.merchantAuthentication = merchant_auth
            sanitized_ref = self._sanitize_ref_id(request.ref_id)
            if sanitized_ref:
                create_transaction_request.refId = sanitized_ref
            create_transaction_request.transactionRequest = transaction_request

            controller = createTransactionController(create_transaction_request)
            controller.setenvironment(self._get_environment())
            controller.execute()

            response = controller.getresponse()
            return self._parse_response(response)

        except AuthorizeNetValidationError:
            raise
        except Exception as e:
            logger.error("Authorize.Net API error", error=str(e), exc_info=True)
            raise AuthorizeNetConnectionError(f"Failed to connect to Authorize.Net: {str(e)}")

    def capture(self, request: CaptureRequest) -> TransactionResponse:
        """Capture a previously authorized transaction"""
        try:
            merchant_auth = self._create_merchant_auth()

            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "priorAuthCaptureTransaction"
            transaction_request.refTransId = request.transaction_id
            transaction_request.amount = str(request.amount)

            create_transaction_request = apicontractsv1.createTransactionRequest()
            create_transaction_request.merchantAuthentication = merchant_auth
            sanitized_ref = self._sanitize_ref_id(request.ref_id)
            if sanitized_ref:
                create_transaction_request.refId = sanitized_ref
            create_transaction_request.transactionRequest = transaction_request

            controller = createTransactionController(create_transaction_request)
            controller.setenvironment(self._get_environment())
            controller.execute()

            response = controller.getresponse()
            return self._parse_response(response)

        except AuthorizeNetValidationError:
            raise
        except Exception as e:
            logger.error("Authorize.Net API error", error=str(e), exc_info=True)
            raise AuthorizeNetConnectionError(f"Failed to connect to Authorize.Net: {str(e)}")

    def void(self, request: VoidRequest) -> TransactionResponse:
        """Void (cancel) a previously authorized/unsettled transaction"""
        try:
            merchant_auth = self._create_merchant_auth()

            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "voidTransaction"
            transaction_request.refTransId = request.transaction_id

            create_transaction_request = apicontractsv1.createTransactionRequest()
            create_transaction_request.merchantAuthentication = merchant_auth
            sanitized_ref = self._sanitize_ref_id(request.ref_id)
            if sanitized_ref:
                create_transaction_request.refId = sanitized_ref
            create_transaction_request.transactionRequest = transaction_request

            controller = createTransactionController(create_transaction_request)
            controller.setenvironment(self._get_environment())
            controller.execute()

            response = controller.getresponse()
            return self._parse_response(response)

        except AuthorizeNetValidationError:
            raise
        except Exception as e:
            logger.error("Authorize.Net API error", error=str(e), exc_info=True)
            raise AuthorizeNetConnectionError(f"Failed to connect to Authorize.Net: {str(e)}")

    def refund(self, request: RefundRequest) -> TransactionResponse:
        """Refund a captured/settled transaction"""
        try:
            merchant_auth = self._create_merchant_auth()

            credit_card = apicontractsv1.creditCardType()
            credit_card.cardNumber = request.card_number_last4
            credit_card.expirationDate = "XXXX"  # per Authorize.Net sample for refunds

            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card

            transaction_request = apicontractsv1.transactionRequestType()
            transaction_request.transactionType = "refundTransaction"
            transaction_request.amount = str(request.amount)
            transaction_request.refTransId = request.transaction_id
            transaction_request.payment = payment

            create_transaction_request = apicontractsv1.createTransactionRequest()
            create_transaction_request.merchantAuthentication = merchant_auth
            sanitized_ref = self._sanitize_ref_id(request.ref_id)
            if sanitized_ref:
                create_transaction_request.refId = sanitized_ref
            create_transaction_request.transactionRequest = transaction_request

            controller = createTransactionController(create_transaction_request)
            controller.setenvironment(self._get_environment())
            controller.execute()

            response = controller.getresponse()
            return self._parse_response(response)

        except AuthorizeNetValidationError:
            raise
        except Exception as e:
            logger.error("Authorize.Net API error", error=str(e), exc_info=True)
            raise AuthorizeNetConnectionError(f"Failed to connect to Authorize.Net: {str(e)}")

    def create_subscription(self, request: SubscriptionRequest) -> SubscriptionResponse:
        """Create a recurring subscription (ARB)"""
        try:
            merchant_auth = self._create_merchant_auth()

            # payment schedule
            schedule = apicontractsv1.paymentScheduleType()
            interval = apicontractsv1.paymentScheduleTypeInterval()
            interval.length = request.schedule.interval_length
            unit = request.schedule.interval_unit.lower()
            if unit == "days":
                interval.unit = apicontractsv1.ARBSubscriptionUnitEnum.days
            elif unit == "months":
                interval.unit = apicontractsv1.ARBSubscriptionUnitEnum.months
            else:
                raise AuthorizeNetValidationError("interval_unit must be 'days' or 'months'")
            schedule.interval = interval
            schedule.startDate = request.schedule.start_date
            schedule.totalOccurrences = request.schedule.total_occurrences
            schedule.trialOccurrences = request.schedule.trial_occurrences

            # payment info
            credit_card = apicontractsv1.creditCardType()
            credit_card.cardNumber = request.credit_card.card_number.replace(" ", "").replace("-", "")
            exp_date = request.credit_card.expiration_date
            if len(exp_date) == 7 and "-" in exp_date:  # YYYY-MM format
                year, month = exp_date.split("-")
                exp_date = f"{month}/{year[-2:]}"
            credit_card.expirationDate = exp_date
            if request.credit_card.card_code:
                credit_card.cardCode = request.credit_card.card_code

            payment = apicontractsv1.paymentType()
            payment.creditCard = credit_card

            bill_to = apicontractsv1.nameAndAddressType()
            bill_to.firstName = request.customer_address.first_name
            bill_to.lastName = request.customer_address.last_name
            if request.customer_address.company:
                bill_to.company = request.customer_address.company
            bill_to.address = request.customer_address.address
            bill_to.city = request.customer_address.city
            bill_to.state = request.customer_address.state
            bill_to.zip = request.customer_address.zip
            bill_to.country = request.customer_address.country

            subscription = apicontractsv1.ARBSubscriptionType()
            subscription.name = request.name
            subscription.paymentSchedule = schedule
            subscription.amount = float(request.amount)
            subscription.trialAmount = float(request.schedule.trial_amount)
            subscription.billTo = bill_to
            subscription.payment = payment

            arb_request = apicontractsv1.ARBCreateSubscriptionRequest()
            arb_request.merchantAuthentication = merchant_auth
            sanitized_ref = self._sanitize_ref_id(request.ref_id)
            if sanitized_ref:
                arb_request.refId = sanitized_ref
            arb_request.subscription = subscription

            controller = ARBCreateSubscriptionController(arb_request)
            controller.setenvironment(self._get_environment())
            controller.execute()

            response = controller.getresponse()
            return self._parse_subscription_response(response)

        except AuthorizeNetValidationError:
            raise
        except Exception as e:
            logger.error("Authorize.Net API error", error=str(e), exc_info=True)
            raise AuthorizeNetConnectionError(f"Failed to connect to Authorize.Net: {str(e)}")

    def _parse_subscription_response(self, response) -> SubscriptionResponse:
        """Parse ARB subscription response"""
        if response is None:
            return SubscriptionResponse(
                success=False,
                error_text="Null response from Authorize.Net",
            )

        result_code = response.messages.resultCode
        if result_code == "Ok":
            msg = response.messages.message[0]
            return SubscriptionResponse(
                success=True,
                subscription_id=str(getattr(response, "subscriptionId", None)),
                result_code=result_code,
                message_code=str(msg.code),
                message_text=msg.text,
            )

        # errors
        msg = response.messages.message[0]
        return SubscriptionResponse(
            success=False,
            result_code=result_code,
            error_code=str(msg.code),
            error_text=msg.text,
        )

    def _parse_response(self, response) -> TransactionResponse:
        """Parse Authorize.Net API response"""
        if response is None:
            return TransactionResponse(
                success=False,
                error_text="Null response from Authorize.Net"
            )

        result_code = response.messages.resultCode

        # Check if API request was successful
        if result_code == "Ok":
            # Check for transaction response
            if hasattr(response, 'transactionResponse') and response.transactionResponse:
                trans_response = response.transactionResponse

                # Check for success messages
                if hasattr(trans_response, 'messages') and trans_response.messages:
                    response_code = str(trans_response.responseCode) if hasattr(trans_response, "responseCode") else None
                    message_code = str(trans_response.messages.message[0].code)
                    transaction_id = str(trans_response.transId) if hasattr(trans_response, "transId") else None
                    return TransactionResponse(
                        success=True,
                        transaction_id=transaction_id,
                        response_code=response_code,
                        message_code=message_code,
                        message_description=trans_response.messages.message[0].description,
                        result_code=result_code
                    )
                # Check for errors
                elif hasattr(trans_response, 'errors') and trans_response.errors:
                    error = trans_response.errors.error[0]
                    error_code = str(error.errorCode) if hasattr(error, "errorCode") else None
                    return TransactionResponse(
                        success=False,
                        error_code=error_code,
                        error_text=error.errorText,
                        result_code=result_code
                    )

        # API request failed
        error_code = None
        error_text = None

        if hasattr(response, 'transactionResponse') and hasattr(
            response.transactionResponse, 'errors'
        ) and response.transactionResponse.errors:
            error = response.transactionResponse.errors.error[0]
            error_code = str(error.errorCode)
            error_text = error.errorText
        elif hasattr(response, 'messages') and response.messages.message:
            msg = response.messages.message[0]
            error_code = str(msg.code)
            error_text = msg.text

        return TransactionResponse(
            success=False,
            error_code=error_code,
            error_text=error_text,
            result_code=result_code
        )
