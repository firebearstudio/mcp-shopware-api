import asyncio
import functools
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

# Enhanced logging configuration for debugging
handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]

# Only add file logging when MCP_DEBUG environment variable is set to true or 1
if os.getenv("MCP_DEBUG", "").lower() in ("true", "1"):
    handlers.append(logging.FileHandler("/tmp/mcp-shopware-debug.log", mode="a"))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=handlers,
)

logger = logging.getLogger(__name__)
mcp_logger = logging.getLogger("MCP")
api_logger = logging.getLogger("SHOPWARE_API")


# MCP Communication logger
def log_mcp_call(func: Callable) -> Callable:
    """Decorator to log all MCP tool calls with parameters and results"""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        mcp_logger.info(f"🔧 MCP TOOL CALLED: {tool_name}")
        mcp_logger.info(f"📥 INPUT ARGS: {args}")
        mcp_logger.info(f"📥 INPUT KWARGS: {kwargs}")

        try:
            result = await func(*args, **kwargs)
            mcp_logger.info(f"📤 OUTPUT SUCCESS: {tool_name}")
            mcp_logger.debug(f"📤 OUTPUT DATA: {result}")
            return result
        except Exception as e:
            mcp_logger.error(f"❌ OUTPUT ERROR: {tool_name} - {str(e)}")
            raise

    return wrapper


class ShopwareAuth:
    def __init__(self, store_url: str, api_key: str, api_secret: str):
        self.store_url = store_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.client = httpx.AsyncClient()

    async def _request_new_token(self) -> None:
        auth_url = f"{self.store_url}/api/oauth/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.api_key,
            "client_secret": self.api_secret,
        }

        try:
            response = await self.client.post(auth_url, json=auth_data)
            response.raise_for_status()
            token_data = response.json()

            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)

            logger.info("Successfully obtained new access token")

        except Exception as e:
            logger.error(f"Failed to obtain access token: {e}")
            raise

    async def get_valid_token(self) -> str:
        if (
            self.access_token is None
            or self.token_expires_at is None
            or datetime.now() >= self.token_expires_at
        ):
            await self._request_new_token()

        # After _request_new_token, access_token should be set
        assert self.access_token is not None
        return self.access_token

    async def make_authenticated_request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> httpx.Response:
        token = await self.get_valid_token()
        headers = kwargs.get("headers", {})
        headers.update(
            {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        kwargs["headers"] = headers

        url = f"{self.store_url}/api{endpoint}"

        # Log API request details
        api_logger.info(f"🌐 API REQUEST: {method} {url}")
        if kwargs.get("params"):
            api_logger.debug(f"🔍 REQUEST PARAMS: {kwargs['params']}")
        if kwargs.get("json"):
            api_logger.debug(f"📋 REQUEST BODY: {json.dumps(kwargs['json'], indent=2)}")

        response = await self.client.request(method, url, **kwargs)

        # Log API response details
        api_logger.info(f"📡 API RESPONSE: {method} {url} -> {response.status_code}")
        if response.status_code >= 400:
            api_logger.error(f"❌ ERROR RESPONSE: {response.text}")
        else:
            try:
                response_data = response.json()
                if isinstance(response_data, dict) and "data" in response_data:
                    data_count = (
                        len(response_data["data"])
                        if isinstance(response_data["data"], list)
                        else 1
                    )
                    total = response_data.get("total", "unknown")
                    api_logger.info(
                        f"📊 RESPONSE SUMMARY: {data_count} items (total: {total})"
                    )
                api_logger.debug(
                    f"📦 RESPONSE DATA: {json.dumps(response_data, indent=2)}"
                )
            except:
                api_logger.debug(f"📦 RESPONSE DATA: {response.text}")

        return response


def register_tools(mcp: FastMCP, shopware_auth: ShopwareAuth) -> None:
    """Register all MCP tools with the FastMCP instance"""

    @mcp.tool()
    @log_mcp_call
    async def search_shopware_entities(
        entity: str, search_criteria: Optional[Union[Dict[str, Any], str]] = None
    ) -> str:
        """Universal search tool for any Shopware entity using the Admin API search endpoint.

        This tool provides access to all Shopware entities through a unified search interface.
        It supports the full Shopware search criteria functionality including filtering,
        sorting, associations, aggregations, and pagination.

        **IMPORTANT - Product Variant Filtering**:
        When searching for 'product' entities, this tool automatically adds a filter for parentId = null
        by default, matching the Shopware admin panel behavior (showing only parent products, excluding variants).
        To include ALL products including variants, simply provide your own parentId filter or any other
        filter in your search criteria - this will override the default parent-only behavior.

        Supported Entities (use the entity name as the 'entity' parameter):
        - acl-role, acl-user-role, app, app-action-button, app-payment-method, app-template
        - category, category-tag, cms-block, cms-page, cms-section, cms-slot
        - country, country-state, currency, currency-country-rounding
        - custom-field, custom-field-set, custom-field-set-relation
        - customer, customer-address, customer-group, customer-group-registration-sales-channels
        - customer-recovery, customer-tag, customer-wishlist, customer-wishlist-product
        - dead-message, delivery-time, document, document-base-config
        - document-base-config-sales-channel, document-type
        - event-action, event-action-rule, event-action-sales-channel
        - import-export-file, import-export-log, import-export-profile
        - integration, integration-role, landing-page, landing-page-sales-channel
        - landing-page-tag, language, locale, log-entry
        - mail-header-footer, mail-template, mail-template-media, mail-template-type
        - main-category, media, media-default-folder, media-folder
        - media-folder-configuration, media-folder-configuration-media-thumbnail-size
        - media-tag, media-thumbnail, media-thumbnail-size, message-queue-stats
        - newsletter-recipient, newsletter-recipient-tag, number-range
        - number-range-sales-channel, number-range-state, number-range-type
        - order, order-address, order-customer, order-delivery, order-delivery-position
        - order-line-item, order-tag, order-transaction, payment-method, plugin
        - product, product-category, product-category-tree, product-configurator-setting
        - product-cross-selling, product-cross-selling-assigned-products
        - product-custom-field-set, product-export, product-feature-set
        - product-keyword-dictionary, product-manufacturer, product-media
        - product-option, product-price, product-property, product-review
        - product-search-config, product-search-config-field, product-search-keyword
        - product-sorting, product-stream, product-stream-filter, product-stream-mapping
        - product-tag, product-visibility, promotion, promotion-cart-rule
        - promotion-discount, promotion-discount-prices, promotion-discount-rule
        - promotion-individual-code, promotion-order-rule, promotion-persona-customer
        - promotion-persona-rule, promotion-sales-channel, promotion-setgroup
        - promotion-setgroup-rule, property-group, property-group-option
        - rule, rule-condition, sales-channel, sales-channel-analytics
        - sales-channel-country, sales-channel-currency, sales-channel-domain
        - sales-channel-language, sales-channel-payment-method
        - sales-channel-shipping-method, sales-channel-type, salutation
        - scheduled-task, seo-url, seo-url-template, shipping-method
        - shipping-method-price, shipping-method-tag, snippet, snippet-set
        - state-machine, state-machine-history, state-machine-state
        - state-machine-transition, system-config, tag, tax, tax-rule
        - tax-rule-type, theme, theme-media, theme-sales-channel, unit
        - user, user-access-key, user-config, user-recovery
        - webhook, webhook-event-log

        Args:
            entity: The entity name to search (e.g., 'product', 'order', 'customer')
            search_criteria: Optional search criteria (dict or JSON string) with the following possible parameters:
                - page: integer - Search result page number
                - limit: integer - Number of items per result page
                - filter: array - Array of filter objects for querying data
                - sort: array - Sorting configuration for search results
                - post-filter: array - Post-aggregation filters
                - associations: dict - Load associated entities with their own criteria
                - aggregations: array - Statistical aggregations (avg, count, max, min, stats, sum)
                - grouping: array - Group results by specific fields
                - fields: array - Specific fields to return in results
                - total-count-mode: string - Count calculation mode: 'none', 'exact', 'next-pages'
                - ids: array - List of specific IDs to search for
                - includes: dict - Specify fields to return for given entities

        Filter types supported:
            - contains: Field contains value
            - equalsAny: Field equals any of the provided values
            - prefix: Field starts with value
            - suffix: Field ends with value
            - equals: Field equals exact value
            - range: Field is within range
            - not: Negation filter
            - multi: Multiple conditions with AND/OR

        Example usage:
            # Simple product search with limit (shows only parent products by default)
            search_criteria = {"limit": 5, "page": 1}

            # Search products with custom filter (will include variants since filter is provided)
            search_criteria = {
                "filter": [
                    {"type": "equals", "field": "active", "value": True}
                ],
                "associations": {
                    "manufacturer": {"sort": [{"field": "name", "order": "ASC"}]},
                    "categories": {"limit": 10}
                },
                "sort": [{"field": "name", "order": "ASC"}],
                "limit": 25
            }

            # Explicitly show only parent products
            search_criteria = {
                "filter": [
                    {"type": "equals", "field": "parentId", "value": null}
                ],
                "limit": 25
            }

            # Search orders with customer data
            search_criteria = {
                "associations": {
                    "orderCustomer": {
                        "associations": {
                            "customer": {}
                        }
                    }
                },
                "sort": [{"field": "orderDateTime", "order": "DESC"}]
            }
        """
        try:
            # Handle both dict and JSON string inputs
            criteria: Dict[str, Any]
            if search_criteria is None:
                criteria = {}
            elif isinstance(search_criteria, str):
                try:
                    criteria = json.loads(search_criteria)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in search_criteria: {str(e)}"
            else:
                criteria = search_criteria

            # For product searches, add parentId = null filter by default if no filters are provided
            # This matches Shopware admin panel behavior (showing only parent products, not variants)
            if entity == "product" and "filter" not in criteria:
                criteria["filter"] = [
                    {"type": "equals", "field": "parentId", "value": None}
                ]

            # Use POST /api/search/{entity} endpoint
            endpoint = f"/search/{entity}"

            response = await shopware_auth.make_authenticated_request(
                "POST", endpoint, json=criteria
            )

            if response.status_code == 200:
                result = response.json()
                data_count = len(result.get("data", []))
                total = result.get("total", "unknown")

                return f"Search successful for entity '{entity}'. Retrieved {data_count} items (total: {total}). Result: {result}"
            else:
                return f"Search failed for entity '{entity}' with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error searching entity '{entity}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def search_shopware_entity_ids(
        entity: str, search_criteria: Optional[Union[Dict[str, Any], str]] = None
    ) -> str:
        """Search for entity IDs only using the Shopware Admin API search-ids endpoint.

        This is a lightweight version of the search that returns only matching IDs instead
        of full entity data. Useful for performance when you only need to know which
        entities match your criteria, or for subsequent detailed queries.

        **IMPORTANT - Product Variant Filtering**:
        Like search_shopware_entities, when searching for 'product' entity IDs, this tool automatically
        adds a filter for parentId = null by default (showing only parent product IDs, excluding variants).
        To include ALL product IDs including variants, provide your own filter in the search criteria.

        Args:
            entity: The entity name to search (same entities as search_shopware_entities)
            search_criteria: Optional search criteria (dict or JSON string, same format as search_shopware_entities)
                Note: 'fields' and 'includes' parameters are ignored for ID-only searches

        Returns:
            A list of matching entity IDs
        """
        try:
            # Handle both dict and JSON string inputs
            criteria: Dict[str, Any]
            if search_criteria is None:
                criteria = {}
            elif isinstance(search_criteria, str):
                try:
                    criteria = json.loads(search_criteria)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in search_criteria: {str(e)}"
            else:
                criteria = search_criteria

            # For product searches, add parentId = null filter by default if no filters are provided
            # This matches Shopware admin panel behavior (showing only parent products, not variants)
            if entity == "product" and "filter" not in criteria:
                criteria["filter"] = [
                    {"type": "equals", "field": "parentId", "value": None}
                ]

            # Use POST /api/search-ids/{entity} endpoint
            endpoint = f"/search-ids/{entity}"

            response = await shopware_auth.make_authenticated_request(
                "POST", endpoint, json=criteria
            )

            if response.status_code == 200:
                result = response.json()
                data_count = len(result.get("data", []))
                total = result.get("total", "unknown")

                return f"ID search successful for entity '{entity}'. Found {data_count} matching IDs (total: {total}). Result: {result}"
            else:
                return f"ID search failed for entity '{entity}' with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error searching entity IDs for '{entity}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def get_shopware_entity_by_id(
        entity: str,
        entity_id: str,
        associations: Optional[Union[Dict[str, Any], str]] = None,
    ) -> str:
        """Get a single Shopware entity by its ID using the Admin API detail endpoint.

        This tool fetches a specific entity instance by its unique identifier.
        Optionally loads associated entities in the same request for efficiency.

        Args:
            entity: The entity name (same entities as search_shopware_entities)
            entity_id: The unique ID of the entity to fetch
            associations: Optional associations to load with the entity (dict or JSON string, same format as in search criteria)

        Example usage:
            # Get a product by ID
            get_shopware_entity_by_id("product", "b7d2554b0ce847cd82f3ac9bd1c0dfcd")

            # Get a product with its manufacturer and categories
            associations = {
                "manufacturer": {},
                "categories": {"limit": 10, "sort": [{"field": "name", "order": "ASC"}]}
            }
            get_shopware_entity_by_id("product", "b7d2554b0ce847cd82f3ac9bd1c0dfcd", associations)
        """
        try:
            # Handle both dict and JSON string inputs for associations
            if associations is not None and isinstance(associations, str):
                try:
                    associations = json.loads(associations)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in associations: {str(e)}"

            # Use GET /api/{entity}/{id} endpoint
            endpoint = f"/{entity}/{entity_id}"

            # Add associations as query parameters if provided
            params = {}
            if associations:
                # Shopware expects associations as a JSON string in query params for GET requests
                params["associations"] = json.dumps(associations)

            response = await shopware_auth.make_authenticated_request(
                "GET", endpoint, params=params if params else None
            )

            if response.status_code == 200:
                result = response.json()
                return f"Successfully retrieved {entity} with ID '{entity_id}'. Result: {result}"
            elif response.status_code == 404:
                return f"Entity '{entity}' with ID '{entity_id}' not found."
            else:
                return f"Failed to retrieve {entity} with ID '{entity_id}'. Status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error retrieving {entity} with ID '{entity_id}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def shopware_get_request(
        endpoint: str, params: Optional[Union[Dict[str, Any], str]] = None
    ) -> str:
        """Make a GET request to any Shopware Admin API endpoint.

        This is a unified tool for making GET requests to any endpoint in the Shopware Admin API.
        It automatically handles authentication and provides access to all available endpoints.

        Args:
            endpoint: The API endpoint to call (without /api prefix, e.g., '/product', '/order', '/customer')
            params: Optional query parameters (dict or JSON string) to include in the request

        Examples:
            # Get all products with pagination
            shopware_get_request('/product', {'limit': 10, 'page': 1})

            # Get specific product by ID
            shopware_get_request('/product/b7d2554b0ce847cd82f3ac9bd1c0dfcd')

            # Get orders with associations
            shopware_get_request('/order', {'associations': '{"orderCustomer": {}}'})

            # Get OpenAPI schema
            shopware_get_request('/_info/openapi3.json')

            # Get entity definitions
            shopware_get_request('/_info/open-api-schema.json')
        """
        try:
            # Handle both dict and JSON string inputs for params
            if params is not None and isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in params: {str(e)}"

            # Ensure endpoint starts with /
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint

            response = await shopware_auth.make_authenticated_request(
                "GET", endpoint, params=params
            )

            if response.status_code == 200:
                result = response.json()
                return f"GET request successful for endpoint '{endpoint}'. Result: {result}"
            else:
                return f"GET request failed for endpoint '{endpoint}' with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error making GET request to '{endpoint}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def shopware_post_request(
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Union[Dict[str, Any], str]] = None,
    ) -> str:
        """Make a POST request to any Shopware Admin API endpoint.

        This is a unified tool for making POST requests to any endpoint in the Shopware Admin API.
        It automatically handles authentication and provides access to all available endpoints.

        Args:
            endpoint: The API endpoint to call (without /api prefix, e.g., '/search/product', '/product')
            data: Optional request body data (dict or JSON string) to send in the request
            params: Optional query parameters (dict or JSON string) to include in the request

        Examples:
            # Search products
            data = {"filter": [{"type": "equals", "field": "active", "value": True}], "limit": 10}
            shopware_post_request('/search/product', data)

            # Create a new product
            data = {"name": "New Product", "productNumber": "SW10001", "stock": 10, "price": [{"currencyId": "...", "gross": 19.99}]}
            shopware_post_request('/product', data)

            # Search for entity IDs
            data = {"filter": [{"type": "contains", "field": "name", "value": "test"}]}
            shopware_post_request('/search-ids/product', data)
        """
        try:
            # Handle both dict and JSON string inputs
            if data is not None and isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in data: {str(e)}"

            if params is not None and isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in params: {str(e)}"

            # Ensure endpoint starts with /
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint

            response = await shopware_auth.make_authenticated_request(
                "POST", endpoint, json=data, params=params
            )

            if response.status_code in [200, 201]:
                result = response.json()
                return f"POST request successful for endpoint '{endpoint}'. Result: {result}"
            else:
                return f"POST request failed for endpoint '{endpoint}' with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error making POST request to '{endpoint}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def get_entity_openapi_schema(entity: str) -> str:
        """Get the OpenAPI schema definition for a specific entity.

        This tool fetches the OpenAPI schema from the Shopware API and extracts
        the schema definition for the specified entity. This includes endpoint
        definitions, request/response schemas, and available operations.

        Args:
            entity: The entity name to get the schema for (e.g., 'product', 'order', 'customer')

        Returns:
            The OpenAPI schema definition for the specified entity including all endpoints and schemas
        """
        try:
            # Get the full OpenAPI schema
            response = await shopware_auth.make_authenticated_request(
                "GET", "/_info/openapi3.json"
            )

            if response.status_code != 200:
                return f"Failed to fetch OpenAPI schema with status {response.status_code}: {response.text}"

            openapi_data = response.json()

            # Find paths related to the entity
            entity_paths = {}
            entity_schemas = {}

            # Convert entity name to different formats used in OpenAPI
            entity_kebab = entity.lower().replace("_", "-")
            entity_pascal = "".join(
                word.capitalize() for word in entity.replace("-", "_").split("_")
            )

            # Search for paths
            paths = openapi_data.get("paths", {})
            for path, path_data in paths.items():
                # Check if path is related to the entity
                if (
                    f"/{entity_kebab}" in path
                    or f"/{entity}" in path
                    or entity_kebab in path.lower()
                    or entity in path.lower()
                ):
                    entity_paths[path] = path_data

            # Search for schemas
            components = openapi_data.get("components", {})
            schemas = components.get("schemas", {})
            for schema_name, schema_data in schemas.items():
                if (
                    schema_name.lower() == entity_pascal.lower()
                    or schema_name.lower() == entity_kebab.lower()
                    or schema_name.lower() == entity.lower()
                ):
                    entity_schemas[schema_name] = schema_data

            if not entity_paths and not entity_schemas:
                return f"No OpenAPI schema found for entity '{entity}'. Available entities can be found using get_available_entities tool."

            result = {
                "entity": entity,
                "paths": entity_paths,
                "schemas": entity_schemas,
            }

            return (
                f"OpenAPI schema for entity '{entity}': {json.dumps(result, indent=2)}"
            )

        except Exception as e:
            return f"Error getting OpenAPI schema for entity '{entity}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def get_entity_definition(entity: str) -> str:
        """Get the entity definition from Shopware's open-api-schema.json.

        This tool fetches the entity definitions from the Shopware API which contain
        the structure, properties, and relationships for each entity type.

        Args:
            entity: The entity name to get the definition for (e.g., 'product', 'order', 'customer')

        Returns:
            The entity definition including properties, types, and relationships
        """
        try:
            # Get the entity definitions schema
            response = await shopware_auth.make_authenticated_request(
                "GET", "/_info/open-api-schema.json"
            )

            if response.status_code != 200:
                return f"Failed to fetch entity definitions with status {response.status_code}: {response.text}"

            schema_data = response.json()

            # Convert entity name to match the schema format
            entity_key = entity.lower().replace("_", "-")

            # Look for the entity in the schema
            if entity_key in schema_data:
                entity_definition = schema_data[entity_key]
                result = {"entity": entity, "definition": entity_definition}
                return (
                    f"Entity definition for '{entity}': {json.dumps(result, indent=2)}"
                )

            # If not found, try alternative formats
            for key in schema_data.keys():
                if key.lower() == entity.lower() or key.lower().replace(
                    "-", "_"
                ) == entity.lower().replace("-", "_"):
                    entity_definition = schema_data[key]
                    result = {
                        "entity": entity,
                        "definition": entity_definition,
                        "matched_key": key,
                    }
                    return f"Entity definition for '{entity}' (matched as '{key}'): {json.dumps(result, indent=2)}"

            return f"Entity definition not found for '{entity}'. Available entities can be found using get_available_entities tool."

        except Exception as e:
            return f"Error getting entity definition for entity '{entity}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def shopware_patch_request(
        endpoint: str,
        data: Optional[Union[Dict[str, Any], str]] = None,
        params: Optional[Union[Dict[str, Any], str]] = None,
    ) -> str:
        """Make a PATCH request to any Shopware Admin API endpoint.

        This is a unified tool for making PATCH requests to update entities in the Shopware Admin API.
        It automatically handles authentication and provides access to all available endpoints.

        Args:
            endpoint: The API endpoint to call (without /api prefix, e.g., '/product/{id}', '/order/{id}')
            data: Optional request body data (dict or JSON string) with the fields to update
            params: Optional query parameters (dict or JSON string) to include in the request

        Examples:
            # Update a product
            data = {"name": "Updated Product Name", "active": True}
            shopware_patch_request('/product/b7d2554b0ce847cd82f3ac9bd1c0dfcd', data)

            # Update order status
            data = {"orderState": "completed"}
            shopware_patch_request('/order/12345', data)

            # Update customer information
            data = {"firstName": "John", "lastName": "Doe", "email": "john.doe@example.com"}
            shopware_patch_request('/customer/customer-id', data)
        """
        try:
            # Handle both dict and JSON string inputs
            if data is not None and isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in data: {str(e)}"

            if params is not None and isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in params: {str(e)}"

            # Ensure endpoint starts with /
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint

            response = await shopware_auth.make_authenticated_request(
                "PATCH", endpoint, json=data, params=params
            )

            if response.status_code in [200, 204]:
                if response.status_code == 204:
                    return f"PATCH request successful for endpoint '{endpoint}'. Entity updated (no content returned)."
                else:
                    result = response.json()
                    return f"PATCH request successful for endpoint '{endpoint}'. Result: {result}"
            else:
                return f"PATCH request failed for endpoint '{endpoint}' with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error making PATCH request to '{endpoint}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def shopware_delete_request(
        endpoint: str,
        params: Optional[Union[Dict[str, Any], str]] = None,
    ) -> str:
        """Make a DELETE request to any Shopware Admin API endpoint.

        This is a unified tool for making DELETE requests to remove entities from the Shopware Admin API.
        It automatically handles authentication and provides access to all available endpoints.

        Args:
            endpoint: The API endpoint to call (without /api prefix, e.g., '/product/{id}', '/order/{id}')
            params: Optional query parameters (dict or JSON string) to include in the request

        Examples:
            # Delete a product
            shopware_delete_request('/product/b7d2554b0ce847cd82f3ac9bd1c0dfcd')

            # Delete an order
            shopware_delete_request('/order/12345')

            # Delete a customer
            shopware_delete_request('/customer/customer-id')

            # Delete with additional parameters
            shopware_delete_request('/product/product-id', {'force': 'true'})
        """
        try:
            # Handle both dict and JSON string inputs for params
            if params is not None and isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in params: {str(e)}"

            # Ensure endpoint starts with /
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint

            response = await shopware_auth.make_authenticated_request(
                "DELETE", endpoint, params=params
            )

            if response.status_code in [200, 204]:
                if response.status_code == 204:
                    return f"DELETE request successful for endpoint '{endpoint}'. Entity deleted successfully."
                else:
                    result = response.json()
                    return f"DELETE request successful for endpoint '{endpoint}'. Result: {result}"
            else:
                return f"DELETE request failed for endpoint '{endpoint}' with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error making DELETE request to '{endpoint}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def shopware_sync_operation(
        entity: str,
        action: str,
        payload: Union[List[Dict[str, Any]], List[str], str],
        operation_key: Optional[str] = None,
        indexing_behavior: Optional[str] = None,
        skip_trigger_flow: bool = False,
    ) -> str:
        """Execute bulk operations using Shopware's Sync API for high-performance batch processing.

        The Sync API allows you to perform multiple write operations (creating/updating and deleting)
        simultaneously. This is much more efficient than individual API calls for bulk operations.

        **IMPORTANT**: This tool creates a single sync operation. If you need multiple different
        operations (e.g., upsert products AND delete categories), you should use shopware_post_request
        with the full sync payload format.

        Args:
            entity: The Shopware entity name (e.g., 'product', 'category', 'customer', 'order', etc.)
            action: The operation type - either 'upsert' or 'delete'
                - 'upsert': Insert new entities or update existing ones (requires entity data objects)
                - 'delete': Remove entities (requires entity IDs or foreign key combinations)
            payload: The operation payload (list or JSON string):
                - For 'upsert': List of entity data objects with fields to create/update
                - For 'delete': List of ID objects or foreign key combinations for mapping entities
            operation_key: Optional operation key for debugging (auto-generated if not provided)
            indexing_behavior: Optional performance optimization header. Values:
                - None (default): Data will be indexed synchronously
                - 'use-queue-indexing': Data will be indexed asynchronously (better performance)
                - 'disable-indexing': Data indexing is completely disabled (fastest)
            skip_trigger_flow: If True, skips business logic flows (sw-skip-trigger-flow header)

        **Payload Format Examples**:

        **UPSERT Operations** (Create/Update entities):
        ```python
        # Simple entities with data
        payload = [
            {"name": "New Product", "stock": 100, "active": True},
            {"id": "existing-id", "name": "Updated Product", "stock": 50}
        ]

        # Categories with hierarchy
        payload = [
            {"name": "Electronics", "active": True},
            {"name": "Computers", "parentId": "parent-category-id"}
        ]

        # Products with prices
        payload = [
            {
                "name": "Laptop",
                "productNumber": "LP001",
                "stock": 10,
                "price": [{"currencyId": "currency-id", "gross": 999.99}],
                "taxId": "tax-id"
            }
        ]
        ```

        **DELETE Operations** (Remove entities):
        ```python
        # Simple entities by ID
        payload = [
            {"id": "entity-id-1"},
            {"id": "entity-id-2"}
        ]

        # Mapping entities by foreign keys (e.g., product_category)
        payload = [
            {"productId": "prod-id-1", "categoryId": "cat-id-1"},
            {"productId": "prod-id-2", "categoryId": "cat-id-1"}
        ]

        # Product properties by composite keys
        payload = [
            {"productId": "prod-id", "optionId": "option-id"}
        ]
        ```

        **Performance Optimization**:
        For large bulk operations, use performance parameters:
        - `indexing_behavior='use-queue-indexing'` - Index asynchronously (recommended for bulk imports)
        - `indexing_behavior='disable-indexing'` - Disable indexing completely (fastest, manual indexing required)
        - `skip_trigger_flow=True` - Skip business logic flows and events (faster processing)

        **Common Use Cases**:
        1. **Bulk Product Import**: Create/update hundreds of products efficiently
        2. **Stock Updates**: Update inventory levels for multiple products
        3. **Category Management**: Create category hierarchies or bulk delete
        4. **Customer Data**: Import customer lists or update customer information
        5. **Order Processing**: Bulk update order statuses or create test orders
        6. **Cleanup Operations**: Delete outdated entities or broken relations

        **Error Handling**:
        The sync API is transactional - if one operation fails, the entire request is rolled back.
        Check the response for details about created, updated, or deleted entities.

        Examples:
            # Create multiple products (basic)
            shopware_sync_operation("product", "upsert", [
                {"name": "Product 1", "productNumber": "P001", "stock": 10},
                {"name": "Product 2", "productNumber": "P002", "stock": 5}
            ])

            # Bulk import with performance optimization
            shopware_sync_operation("product", "upsert", [
                {"name": "Product 1", "productNumber": "P001", "stock": 10},
                {"name": "Product 2", "productNumber": "P002", "stock": 5}
            ], indexing_behavior="use-queue-indexing", skip_trigger_flow=True)

            # High-performance bulk operation (fastest)
            shopware_sync_operation("product", "upsert", [
                {"name": "Product 1", "productNumber": "P001", "stock": 10}
            ], indexing_behavior="disable-indexing", skip_trigger_flow=True)

            # Update existing products by ID
            shopware_sync_operation("product", "upsert", [
                {"id": "product-uuid", "stock": 100, "active": True}
            ])

            # Delete multiple categories
            shopware_sync_operation("category", "delete", [
                {"id": "category-id-1"},
                {"id": "category-id-2"}
            ])

            # Remove product-category associations
            shopware_sync_operation("product_category", "delete", [
                {"productId": "prod-id", "categoryId": "cat-id"}
            ])
        """
        try:
            # Handle JSON string input
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError as e:
                    return f"Invalid JSON in payload: {str(e)}"

            # Validate action
            if action not in ["upsert", "delete"]:
                return f"Invalid action '{action}'. Must be 'upsert' or 'delete'."

            # Validate indexing_behavior
            valid_indexing_behaviors = [None, "use-queue-indexing", "disable-indexing"]
            if indexing_behavior not in valid_indexing_behaviors:
                return f"Invalid indexing_behavior '{indexing_behavior}'. Must be one of: {valid_indexing_behaviors}"

            # Validate payload is a list
            if not isinstance(payload, list):
                return f"Payload must be a list of objects (for upsert) or IDs (for delete)."

            # Generate operation key if not provided
            if operation_key is None:
                operation_key = f"{action}-{entity}"

            # Construct sync payload
            sync_payload = {
                operation_key: {"entity": entity, "action": action, "payload": payload}
            }

            # Prepare additional headers for performance optimization
            extra_headers: Dict[str, str] = {}
            if indexing_behavior is not None:
                extra_headers["indexing-behavior"] = indexing_behavior
            if skip_trigger_flow:
                extra_headers["sw-skip-trigger-flow"] = "1"

            # Make request to sync endpoint with performance headers
            kwargs: Dict[str, Any] = {"json": sync_payload}
            if extra_headers:
                kwargs["headers"] = extra_headers

            response = await shopware_auth.make_authenticated_request(
                "POST", "/_action/sync", **kwargs
            )

            if response.status_code in [200, 201]:
                result = response.json()

                # Extract key information from response
                data = result.get("data", {})
                not_found = result.get("notFound", [])
                deleted = result.get("deleted", [])

                summary = []
                if data:
                    for entity_type, entity_data in data.items():
                        if isinstance(entity_data, list):
                            summary.append(f"{entity_type}: {len(entity_data)} items")
                        else:
                            summary.append(f"{entity_type}: 1 item")

                summary_text = "; ".join(summary) if summary else "No data returned"

                # Add performance info to response
                perf_info = []
                if indexing_behavior:
                    perf_info.append(f"indexing: {indexing_behavior}")
                if skip_trigger_flow:
                    perf_info.append("flows: skipped")
                perf_text = (
                    f" (Performance: {', '.join(perf_info)})" if perf_info else ""
                )

                return f"Sync operation '{operation_key}' successful. {summary_text}. Not found: {len(not_found)}, Deleted: {len(deleted)}.{perf_text} Full result: {result}"
            else:
                return f"Sync operation failed with status {response.status_code}: {response.text}"

        except Exception as e:
            return f"Error executing sync operation for entity '{entity}': {str(e)}"

    @mcp.tool()
    @log_mcp_call
    async def get_available_entities() -> str:
        """Get a list of all available entity names from Shopware.

        This tool fetches the entity definitions schema and returns a list of all
        available entity names that can be used with other tools.

        Returns:
            A list of all available entity names in the Shopware system
        """
        try:
            # Get the entity definitions schema
            response = await shopware_auth.make_authenticated_request(
                "GET", "/_info/open-api-schema.json"
            )

            if response.status_code != 200:
                return f"Failed to fetch entity definitions with status {response.status_code}: {response.text}"

            schema_data = response.json()

            # Extract all entity names
            entity_names = list(schema_data.keys())
            entity_names.sort()  # Sort alphabetically for easier reading

            result = {"total_entities": len(entity_names), "entities": entity_names}

            return f"Available entities ({len(entity_names)} total): {json.dumps(result, indent=2)}"

        except Exception as e:
            return f"Error getting available entities: {str(e)}"
