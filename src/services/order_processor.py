import logging
logger = logging.getLogger(__name__)
from datetime import datetime
from report_status import report_status

class OrderProcessor:
    def __init__(
        self,
        repository,
        first_handler,
        change_handler,
        emailer
    ):
        self.repository = repository
        self.first_handler = first_handler
        self.change_handler = change_handler
        self.emailer=emailer

    def process(self, order):
        today = datetime.today().strftime("%A")
        #on change
        self.change_handler.process(order)
        #Lock On Price
        if self.repository.lock_if_below_floor(order.id):
            violations = self.repository.get_price_floor_violations(
                order.id
            )
            violationList =f"Order locked {violations[0].C_NUMBER}:"
            for row in violations:
                violationList+=f"\nproduct {row.C_CODE} was sold at £{row.C_NETPRICEBASE:.2f} which is below the minimum price £{row.C_D_PRICEFLOOR:.2f}"
            
            violationList +="\n\nIf your customer needs an exception for a period please contact Daryl/Aaron"
            logger.info(violationList)
            report_status("Order Locked For Price","ok", order.number, "1h", 1)
            self.emailer.send_price_floor_alert(violations[0].C_NUMBER,violationList,row.C_EMAILADDRESS)
        #Run R3-R4 update
        if today not in ("Monday", "Tuesday"):
            r3_r4Log = self.repository.update_run_generation_flags()
            if(r3_r4Log):
                report_status("R3-R4 Flag Change","ok", r3_r4Log, "1d", 3)
        else:
            r3_r4PickLog = self.repository.make_r3_r4_pickable()
            if(r3_r4PickLog):
                report_status("R3-R4 Made Pickable","ok", r3_r4PickLog, "1w", 1)

        #on creation
        if order.processed_once is None or order.processed_once == 0:
            self.first_handler.process(order)
            #Hold Web and Logo Orders
            holdMessage=self.repository.hold_web_and_logo_orders(order.id)
            if holdMessage:
                report_status("New Order Held","ok", order.number, "10m", 2)
            #Delete Carraige charges off orders
            deleteMessage=self.repository.delete_carriage_charges(order.id)
            if deleteMessage:
                report_status("Carriage Charge Deleted","ok", order.number, "10m", 2)

            #Mark order as procssed
            self.repository.mark_processed(
                order.id
            )
