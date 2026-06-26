import pyodbc
from models.sales_order import SalesOrder
import logging
import time
logger = logging.getLogger(__name__)

class SalesOrderRepository:

#Methods for all 
    def __init__(self, connection_string):
        self.connection_string = connection_string

    def _with_retry(
            self,
            operation
        ):
            for attempt in range(3):
                try:
                    return operation()
                except pyodbc.Error as ex:
                    if "1205" in str(ex):
                        logger.warning(
                            "Deadlock detected. Retry %s/3",
                            attempt + 1
                        )
                        time.sleep(0.5)
                        continue
                    logger.exception(
                        "SQL operation failed"
                    )
                    raise

            raise RuntimeError(
                "Operation failed after retries"
            )

    def get_changes(self, last_seen):
        sql = """
        SELECT
            sale.C_ID,
            sale.C_NUMBER,
            sale.C_DOCUMENTLASTUPDATEDON,
            sale.c_d_processedOnce,
            stat.C_CODE
        FROM T_SALESORDER sale WITH (NOLOCK)
        INNER JOIN T_SALESORDERWORKFLOWSTATUS stat WITH (NOLOCK)
            ON sale.C_WORKFLOWSTATUS = stat.C_ID
        WHERE
            stat.C_CODE NOT IN ('SHIPPED','WOFF')
            AND sale.C_DOCUMENTLASTUPDATEDON > ?
            AND sale.C_DATE > '2026-06-23 11:46:00'
        ORDER BY sale.C_DOCUMENTLASTUPDATEDON
        """
        def operation():

            with pyodbc.connect(
                self.connection_string
            ) as conn:

                rows = conn.cursor().execute(
                    sql,
                    last_seen
                ).fetchall()

            return [
                SalesOrder(
                    id=row.C_ID,
                    number=row.C_NUMBER,
                    workflow_status=row.C_CODE,
                    last_updated=row.C_DOCUMENTLASTUPDATEDON,
                    processed_once=row.c_d_processedOnce,
                )
                for row in rows
            ]

        return self._with_retry(operation)

    def mark_processed(self, order_id):
        sql = """
        UPDATE T_SALESORDER
        SET c_d_processedOnce = 1
        WHERE C_ID = ?
        """
        def operation():

            with pyodbc.connect(
                self.connection_string
            ) as conn:

                conn.execute(
                    sql,
                    order_id
                )

                conn.commit()

        self._with_retry(operation)

#Price too low locker
    def lock_if_below_floor(self, order_id):
        sql= """
            UPDATE sale
            SET sale.c_D_DC20AFLOORLOCK = 1, sale.C_DELIVERYAPPROVALSTATUS = 1 
            FROM T_SALESORDER sale
            WHERE sale.c_id = ?
            AND EXISTS
            (
                SELECT 1
                FROM T_SALESORDER_LINE line
                INNER JOIN T_PRODUCT prod
                    ON line.C_PRODUCT = prod.C_ID
                INNER JOIN T_PRODUCT price_controller
                    ON prod.C_D_PRICEFLOORCONTROLPRODUCT = price_controller.C_ID
                INNER JOIN T_CUSTOMER cust
                    ON sale.C_CUSTOMER = cust.C_ID
                LEFT JOIN T_DATABASEASSOCIATION_CUSTOMER_PRODUCT d_ass
                    ON d_ass.C_SECONDITEM = price_controller.C_ID
                    AND d_ass.C_FIRSTITEM = cust.C_ID
                WHERE line.C__OWNER_ = sale.C_ID
                AND line.C_NETPRICEBASE < price_controller.C_D_PRICEFLOOR
                AND (
                        d_ass.C_ASSOCIATIONNAME != 'D_CustomerCanIgnorePriceFloor'
                        OR d_ass.C_ASSOCIATIONNAME IS NULL
                    )
                and (sale.C_D_IGNOREDC20AFLOORLOCK=0
                or sale.C_D_IGNOREDC20AFLOORLOCK is null)
                and (
                    cust.c_d_excludefrompriceflooruntil is null or 
                    cust.c_d_excludefrompriceflooruntil < GETDATE())
            )

            """
        def operation():

            with pyodbc.connect(
                self.connection_string
            ) as conn:

                cursor = conn.execute(
                    sql,
                    order_id
                )

                conn.commit()

                if cursor.rowcount > 0:

                    logger.info(
                        "Applied floor lock to %s",
                        order_id
                    )

                    return True

                return False

        return self._with_retry(operation)

    def get_price_floor_violations(self, order_id):
        sql = """
        SELECT
            sale.C_NUMBER,
            prod.C_CODE,
            line.C_NETPRICEBASE,
            price_controller.C_D_PRICEFLOOR,
			coord.C_EMAILADDRESS
        FROM T_SALESORDER_LINE line
        inner join T_salesorder sale on line.C__OWNER_=sale.C_ID
        INNER JOIN T_PRODUCT prod
            ON line.C_PRODUCT = prod.C_ID
        INNER JOIN T_PRODUCT price_controller
            ON prod.C_D_PRICEFLOORCONTROLPRODUCT = price_controller.C_ID
		inner join T_customer cust on sale.C_CUSTOMER=cust.C_ID
		inner join T_USER coord on cust.C_D_SALESCOORDINATOR=coord.C_ID
        WHERE line.C__OWNER_ = ?
        AND line.C_NETPRICEBASE < price_controller.C_D_PRICEFLOOR
        """

        def operation():

            with pyodbc.connect(
                self.connection_string
            ) as conn:

                return conn.execute(
                    sql,
                    order_id
                ).fetchall()

        return self._with_retry(operation)

#R3-R4 Run Locker/unlocker
    def update_run_generation_flags(self):
        sql = """
        Update T_DELIVERYAGENT
        set c_d_runcangenerate = 
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM T_SALESORDER sale
                    INNER JOIN T_SALESORDERTYPE o_type
                        ON sale.C_ORDERTYPE = o_type.C_ID
                    INNER JOIN T_CUSTOMER cust
                        ON sale.C_CUSTOMER = cust.C_ID
                    INNER JOIN T_CUSTOMERCREDITSTATUS cred_stat
                        ON cust.C_CREDITSTATUS = cred_stat.C_ID
                    INNER JOIN T_DELIVERYAGENT agent
                        ON sale.C_DELIVERYAGENT = agent.C_ID
                    WHERE
                        sale.C_PICKINGNOTESTATUS = 0
                        AND sale.C_DUEDATE <
                        (
                            CASE DATENAME(WEEKDAY, GETDATE())
                                WHEN 'Monday'    THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Tuesday'   THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Wednesday' THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Thursday'  THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Friday'    THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Saturday'  THEN DATEADD(DAY, 6, GETDATE())
                                WHEN 'Sunday'    THEN DATEADD(DAY, 5, GETDATE())
                            END
                        )
                        AND o_type.C_CODE <> '2LO'
                        AND sale.C_D_MANPACKORDER = 0
                        AND cred_stat.C_CODE NOT IN ('4 HOLD','5 STOP','6 LEGAL')
                        AND sale.C_DELIVERYAPPROVALSTATUS <> 1
                        AND agent.C_CODE IN ('R1','R2')
                )
                THEN 1
                ELSE 0
            end
        where C_CODE in ('R3','R4')
        AND c_d_runcangenerate <>
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM T_SALESORDER sale
                    INNER JOIN T_SALESORDERTYPE o_type
                        ON sale.C_ORDERTYPE = o_type.C_ID
                    INNER JOIN T_CUSTOMER cust
                        ON sale.C_CUSTOMER = cust.C_ID
                    INNER JOIN T_CUSTOMERCREDITSTATUS cred_stat
                        ON cust.C_CREDITSTATUS = cred_stat.C_ID
                    INNER JOIN T_DELIVERYAGENT agent
                        ON sale.C_DELIVERYAGENT = agent.C_ID
                    WHERE
                        sale.C_PICKINGNOTESTATUS = 0
                        AND sale.C_DUEDATE <
                        (
                            CASE DATENAME(WEEKDAY, GETDATE())
                                WHEN 'Monday'    THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Tuesday'   THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Wednesday' THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Thursday'  THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Friday'    THEN DATEADD(DAY, 7, GETDATE())
                                WHEN 'Saturday'  THEN DATEADD(DAY, 6, GETDATE())
                                WHEN 'Sunday'    THEN DATEADD(DAY, 5, GETDATE())
                            END
                        )
                        AND o_type.C_CODE <> '2LO'
                        AND sale.C_D_MANPACKORDER = 0
                        AND cred_stat.C_CODE NOT IN ('4 HOLD','5 STOP','6 LEGAL')
                        AND sale.C_DELIVERYAPPROVALSTATUS <> 1
                        AND agent.C_CODE IN ('R1','R2')
                )
                THEN 1
                ELSE 0
            end
        """

        def operation():

            with pyodbc.connect(
                self.connection_string
            ) as conn:

                cursor = conn.execute(sql)

                conn.commit()

            logMessage=None
            if cursor.rowcount > 0:
                logMessage="R3/R4 generation flag changed"
                logger.info(
                    logMessage
                )

                return logMessage

        return self._with_retry(operation)
    
    def make_r3_r4_pickable(self):
        sql=""" 
        Update T_DELIVERYAGENT
        set c_d_runcangenerate = 0
        where C_CODE in ('R3','R4')
         AND c_d_runcangenerate <> 0"""
        
        with pyodbc.connect(
                self.connection_string
            ) as conn:

                cursor = conn.execute(sql)

                conn.commit()

        logMessage=None
        if cursor.rowcount > 0:
            logMessage="R3/R4 set to generate"
            logger.info(
                logMessage
            )
            return logMessage
        return logMessage

    #Web and logo order locker
    def hold_web_and_logo_orders(self, order_id):
        sql=""" 
        UPDATE sale
        SET C_DELIVERYAPPROVALSTATUS =
            CASE
                WHEN 
                    cust.C_D_ALWAYSHOLDNEWORDERS = 1
                    or 
                        (
                            (prod.c_code like '%LOGO%' 
                            or prod.C_DESCRIPTION like '%LOGO%')
                        and prod.C_D_IGNORELOGO=0)
                    OR (
                            sale.C_D_WEBID IS NOT NULL
                            AND (
                                cust.C_D_HOLDWEBORDERS = 1
                                OR useer.C_D_HOLDWEBORDERS = 1
                            )
                        )
                THEN 1
                ELSE 0
            END
        FROM T_SALESORDER sale
        inner join T_SALESORDER_LINE line on line.C__OWNER_=sale.C_ID
        inner join T_PRODUCT prod on line.C_PRODUCT=prod.C_ID
        INNER JOIN T_CUSTOMER cust
            ON sale.C_CUSTOMER = cust.C_ID
        INNER JOIN T_USER useer
            ON useer.C_ID = cust.C_D_SALESCOORDINATOR
        WHERE sale.C_D_WEBID IS NOT NULL
        and sale.c_id=?
        """
        
        with pyodbc.connect(
                self.connection_string
            ) as conn:
                cursor = conn.execute(sql,order_id)
                conn.commit()

        logMessage=None
        if cursor.rowcount > 0:
            logMessage="Order Held"
            logger.info(
                logMessage
            )
            return logMessage
        return logMessage
    
    def delete_carriage_charges(self, order_id):
        sql=""" 
        DELETE FROM T_SALESORDER_LINE
        WHERE C_ID IN (
            SELECT line.C_ID
            FROM T_SALESORDER sale WITH (NOLOCK)
            INNER JOIN T_SALESORDER_LINE line ON line.C__OWNER_ = sale.C_ID
            INNER JOIN T_PRODUCT prod ON line.C_PRODUCT = prod.C_ID
            WHERE sale.C_id = ?
            AND prod.C_CODE = 'CAR03'
        )
        """
        
        with pyodbc.connect(
                self.connection_string
            ) as conn:
                cursor = conn.execute(sql, order_id)
                conn.commit()

        logMessage=None
        if cursor.rowcount > 0:
            logMessage="CAR003 line deleted from order"
            logger.info(
                logMessage
            )
            return logMessage
        return logMessage
