import json

from fastmcp import FastMCP

from .tools import ShopwareAuth


def register_prompts(mcp: FastMCP, shopware_auth: ShopwareAuth) -> None:
    """Register all MCP prompts with the FastMCP instance"""

    @mcp.prompt()
    async def ready_to_ship_orders() -> str:
        """Ready to ship orders

        Automatically retrieve and format all Shopware orders that are paid but not yet shipped.
        This prompt executes the API call and provides instructions for formatting the results.
        """
        try:
            # First, get state machine definitions to extract UUIDs
            state_machine_criteria = {
                "filter": [
                    {
                        "type": "equalsAny",
                        "field": "technicalName",
                        "value": ["order_delivery.state", "order_transaction.state"],
                    }
                ],
                "associations": {
                    "states": {"sort": [{"field": "name", "order": "ASC"}]}
                },
            }

            state_machine_response = await shopware_auth.make_authenticated_request(
                "POST", "/search/state-machine", json=state_machine_criteria
            )

            if state_machine_response.status_code != 200:
                return f"Error retrieving state machines: {state_machine_response.text}"

            state_machines = state_machine_response.json()

            # Extract UUIDs for relevant states
            paid_transaction_states = []
            open_delivery_states = []

            # First, build a lookup map of all states from the included section
            states_lookup = {}
            for item in state_machines.get("included", []):
                if item.get("type") == "state_machine_state":
                    states_lookup[item.get("id")] = item.get("attributes", {})

            # Now process the state machines and look up the actual state details
            for machine in state_machines.get("data", []):
                machine_attrs = machine.get("attributes", {})

                if machine_attrs.get("technicalName") == "order_transaction.state":
                    # Get state IDs from relationships
                    state_refs = (
                        machine.get("relationships", {})
                        .get("states", {})
                        .get("data", [])
                    )
                    for state_ref in state_refs:
                        state_id = state_ref.get("id")
                        state_attrs = states_lookup.get(state_id, {})
                        tech_name = state_attrs.get("technicalName", "")
                        if tech_name in ["paid"]:
                            paid_transaction_states.append(state_id)

                elif machine_attrs.get("technicalName") == "order_delivery.state":
                    # Get state IDs from relationships
                    state_refs = (
                        machine.get("relationships", {})
                        .get("states", {})
                        .get("data", [])
                    )
                    for state_ref in state_refs:
                        state_id = state_ref.get("id")
                        state_attrs = states_lookup.get(state_id, {})
                        tech_name = state_attrs.get("technicalName", "")
                        if tech_name in ["open"]:
                            open_delivery_states.append(state_id)

            if not paid_transaction_states or not open_delivery_states:
                return "Error: Could not find required state machine state UUIDs"

            # Define search criteria for paid but not shipped orders with UUID filtering
            search_criteria = {
                "filter": [
                    {
                        "type": "equalsAny",
                        "field": "transactions.stateMachineState.id",
                        "value": paid_transaction_states,
                    },
                    {
                        "type": "equalsAny",
                        "field": "deliveries.stateMachineState.id",
                        "value": open_delivery_states,
                    },
                ],
                "fields": [
                    "orderNumber",
                    "orderDateTime",
                    "amountTotal",
                    "currencyFactor",
                    "stateMachineState",
                    "orderCustomer",
                    "deliveries",
                    "lineItems",
                    "transactions",
                    "currency",
                ],
                "associations": {
                    "orderCustomer": {"fields": ["firstName", "lastName", "email"]},
                    "deliveries": {
                        "fields": ["shippingDateEarliest", "shippingDateLatest"],
                        "associations": {
                            "stateMachineState": {"fields": ["name", "technicalName"]},
                            "shippingOrderAddress": {
                                "fields": [
                                    "firstName",
                                    "lastName",
                                    "street",
                                    "zipcode",
                                    "city",
                                    "countryId",
                                ],
                                "associations": {"country": {"fields": ["name"]}},
                            },
                        },
                    },
                    "lineItems": {
                        "fields": [
                            "label",
                            "quantity",
                            "unitPrice",
                            "totalPrice",
                            "type",
                        ],
                        "filter": [
                            {"type": "equals", "field": "type", "value": "product"}
                        ],
                        "associations": {
                            "product": {"fields": ["name", "productNumber"]}
                        },
                    },
                    "stateMachineState": {"fields": ["name", "technicalName"]},
                    "transactions": {
                        "fields": ["amount"],
                        "associations": {
                            "stateMachineState": {"fields": ["name", "technicalName"]}
                        },
                    },
                    "currency": {"fields": ["symbol", "isoCode"]},
                },
                "sort": [{"field": "orderDateTime", "order": "DESC"}],
                "limit": 50,
            }

            # Execute the order search
            endpoint = "/search/order"
            response = await shopware_auth.make_authenticated_request(
                "POST", endpoint, json=search_criteria
            )

            if response.status_code == 200:
                orders_data = response.json()

                # Create the combined prompt with data and instructions
                system_prompt = """You are analyzing Shopware order data to identify orders ready for shipping.

TASK: Format the following order data into a clear, readable table showing orders that are paid but not yet shipped.

REQUIRED TABLE COLUMNS:
1. Order Number
2. Product Names (show quantity × unit price for each item)
3. Delivery Name and Address (full shipping address)
4. Order Date (formatted as YYYY-MM-DD)
5. Current Order Status
6. Payment Status
7. Delivery Status

FORMATTING INSTRUCTIONS:
- Use a clean table format with proper alignment
- For products: show "ProductName (Qty: X × $Price = $Total)"
- For address: show "Name, Street, City, ZIP, Country"
- Sort by order date (newest first)
- If no orders found, clearly state "No ready-to-ship orders found"
- Highlight any important status information

DATA TO PROCESS:
"""

                return f"{system_prompt}\n\n{json.dumps(orders_data, indent=2)}"
            else:
                error_prompt = f"""Error retrieving orders: Status {response.status_code}
                
Please inform the user that there was an error retrieving ready-to-ship orders from the Shopware API.
Error details: {response.text}"""
                return error_prompt

        except Exception as e:
            error_prompt = f"""Error executing ready-to-ship orders search: {str(e)}
            
Please inform the user that there was an error executing the ready-to-ship orders search.
Technical details: {str(e)}"""
            return error_prompt
