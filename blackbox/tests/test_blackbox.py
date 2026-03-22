"""
QuickCart API Black-Box Test Suite
Comprehensive testing for the QuickCart REST API
"""

import pytest
import requests

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URL = "http://localhost:8080/api/v1"
ROLL_NUMBER = "2024101122"
USER_ID = "1"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_headers(include_user_id=True, roll_number=ROLL_NUMBER, user_id=USER_ID):
    """Get standard headers for API requests."""
    headers = {}
    if roll_number is not None:
        headers["X-Roll-Number"] = roll_number
    if include_user_id and user_id is not None:
        headers["X-User-ID"] = user_id
    return headers


def get_admin_headers():
    """Get headers for admin endpoints (no X-User-ID needed)."""
    return {"X-Roll-Number": ROLL_NUMBER}


def clear_cart():
    """Clear the user's cart."""
    response = requests.delete(f"{BASE_URL}/cart/clear", headers=get_headers())
    return response


def get_products():
    """Get all available products."""
    response = requests.get(f"{BASE_URL}/products", headers=get_headers())
    if response.status_code == 200:
        return response.json()
    return []


def get_valid_product_id():
    """Get a valid product ID from the products list."""
    products = get_products()
    if products and len(products) > 0:
        if isinstance(products, list):
            return products[0].get("product_id") or products[0].get("id")
        elif isinstance(products, dict) and "products" in products:
            if len(products["products"]) > 0:
                return products["products"][0].get("product_id") or products["products"][0].get("id")
    return None


def get_product_with_stock():
    """Get a product that has stock available."""
    products = get_products()
    if isinstance(products, dict) and "products" in products:
        products = products["products"]
    for product in products:
        stock = product.get("stock", 0)
        if stock > 0:
            return product
    return None


def add_to_cart(product_id, quantity):
    """Add a product to the cart."""
    payload = {"product_id": product_id, "quantity": quantity}
    response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
    return response


def get_cart():
    """Get the current cart."""
    response = requests.get(f"{BASE_URL}/cart", headers=get_headers())
    return response


def get_cart_total():
    """Get the total from the current cart."""
    response = get_cart()
    if response.status_code == 200:
        cart_data = response.json()
        return cart_data.get("total", 0)
    return 0


def get_wallet_balance():
    """Get the user's wallet balance."""
    response = requests.get(f"{BASE_URL}/wallet", headers=get_headers())
    if response.status_code == 200:
        wallet_data = response.json()
        # API returns wallet_balance instead of balance
        return wallet_data.get("wallet_balance", wallet_data.get("balance", 0))
    return 0


def get_admin_users():
    """Get all users via admin endpoint."""
    response = requests.get(f"{BASE_URL}/admin/users", headers=get_admin_headers())
    return response


def get_admin_coupons():
    """Get all coupons via admin endpoint."""
    response = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
    return response


def get_admin_orders():
    """Get all orders via admin endpoint."""
    response = requests.get(f"{BASE_URL}/admin/orders", headers=get_admin_headers())
    return response


def get_orders():
    """Get user's orders."""
    response = requests.get(f"{BASE_URL}/orders", headers=get_headers())
    return response


def remove_coupon():
    """Remove any applied coupon from cart."""
    response = requests.post(f"{BASE_URL}/coupon/remove", headers=get_headers())
    return response


# =============================================================================
# GLOBAL HEADER TESTS
# =============================================================================

class TestGlobalHeaders:
    """Tests for global header requirements."""

    def test_missing_roll_number_returns_401(self):
        """Missing X-Roll-Number header should return 401."""
        headers = {"X-User-ID": USER_ID}
        response = requests.get(f"{BASE_URL}/products", headers=headers)
        assert response.status_code == 401

    def test_invalid_roll_number_letters_returns_400(self):
        """Invalid X-Roll-Number with letters should return 400."""
        headers = {"X-Roll-Number": "abc123", "X-User-ID": USER_ID}
        response = requests.get(f"{BASE_URL}/products", headers=headers)
        assert response.status_code == 400

    def test_invalid_roll_number_symbols_returns_400(self):
        """Invalid X-Roll-Number with symbols should return 400."""
        headers = {"X-Roll-Number": "123!@#", "X-User-ID": USER_ID}
        response = requests.get(f"{BASE_URL}/products", headers=headers)
        assert response.status_code == 400

    def test_missing_user_id_for_user_endpoint_returns_400(self):
        """Missing X-User-ID for user endpoint should return 400."""
        headers = {"X-Roll-Number": ROLL_NUMBER}
        response = requests.get(f"{BASE_URL}/cart", headers=headers)
        assert response.status_code == 400

    def test_invalid_user_id_returns_400(self):
        """Invalid X-User-ID should return 400."""
        headers = {"X-Roll-Number": ROLL_NUMBER, "X-User-ID": "invalid"}
        response = requests.get(f"{BASE_URL}/cart", headers=headers)
        assert response.status_code == 400

    def test_negative_user_id_returns_400(self):
        """Negative X-User-ID should return 400."""
        headers = {"X-Roll-Number": ROLL_NUMBER, "X-User-ID": "-1"}
        response = requests.get(f"{BASE_URL}/cart", headers=headers)
        assert response.status_code == 400

    def test_admin_endpoint_without_user_id_works(self):
        """Admin endpoints should not require X-User-ID."""
        headers = {"X-Roll-Number": ROLL_NUMBER}
        response = requests.get(f"{BASE_URL}/admin/products", headers=headers)
        assert response.status_code == 200


# =============================================================================
# PROFILE TESTS
# =============================================================================

class TestProfile:
    """Tests for Profile endpoints."""

    def test_get_profile_success(self):
        """GET /profile should return user profile."""
        response = requests.get(f"{BASE_URL}/profile", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert "name" in data or "user_id" in data

    def test_update_profile_valid_name(self):
        """PUT /profile with valid name should succeed."""
        payload = {"name": "John Doe", "phone": "1234567890"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 200

    def test_update_profile_name_too_short(self):
        """PUT /profile with name < 2 characters should return 400."""
        payload = {"name": "J", "phone": "1234567890"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_update_profile_name_too_long(self):
        """PUT /profile with name > 50 characters should return 400."""
        payload = {"name": "A" * 51, "phone": "1234567890"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_update_profile_name_boundary_min(self):
        """PUT /profile with name = 2 characters should succeed."""
        payload = {"name": "Jo", "phone": "1234567890"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 200

    def test_update_profile_name_boundary_max(self):
        """PUT /profile with name = 50 characters should succeed."""
        payload = {"name": "A" * 50, "phone": "1234567890"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 200

    def test_update_profile_phone_not_10_digits(self):
        """PUT /profile with phone != 10 digits should return 400."""
        payload = {"name": "John Doe", "phone": "123456789"}  # 9 digits
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_update_profile_phone_too_long(self):
        """PUT /profile with phone > 10 digits should return 400."""
        payload = {"name": "John Doe", "phone": "12345678901"}  # 11 digits
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_update_profile_phone_with_letters(self):
        """PUT /profile with non-numeric phone should return 400."""
        payload = {"name": "John Doe", "phone": "123456789a"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        assert response.status_code == 400

    # --- Bug Tests ---
    def test_bug_profile_accepts_phone_with_letters(self):
        """BUG: PUT /profile accepts non-digit characters in phone."""
        payload = {"name": "John Doe", "phone": "123456789a"}
        response = requests.put(f"{BASE_URL}/profile", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts phone with letters, got {response.status_code}"


# =============================================================================
# ADDRESSES TESTS
# =============================================================================

class TestAddresses:
    """Tests for Addresses endpoints."""

    def test_get_addresses_success(self):
        """GET /addresses should return list of addresses."""
        response = requests.get(f"{BASE_URL}/addresses", headers=get_headers())
        assert response.status_code == 200

    def test_add_address_valid(self):
        """POST /addresses with valid data should succeed."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "Test City",
            "pincode": "123456",
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]
        data = response.json()
        assert "address_id" in data or "address" in data

    def test_add_address_invalid_label(self):
        """POST /addresses with invalid label should return 400."""
        payload = {
            "label": "INVALID",
            "street": "123 Test Street",
            "city": "Test City",
            "pincode": "123456"
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_address_label_office(self):
        """POST /addresses with OFFICE label should succeed."""
        payload = {
            "label": "OFFICE",
            "street": "456 Office Street",
            "city": "Office City",
            "pincode": "654321",
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]

    def test_add_address_label_other(self):
        """POST /addresses with OTHER label should succeed."""
        payload = {
            "label": "OTHER",
            "street": "789 Other Street",
            "city": "Other City",
            "pincode": "111222",
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]

    def test_add_address_street_too_short(self):
        """POST /addresses with street < 5 characters should return 400."""
        payload = {
            "label": "HOME",
            "street": "123",
            "city": "Test City",
            "pincode": "123456"
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_address_street_too_long(self):
        """POST /addresses with street > 100 characters should return 400."""
        payload = {
            "label": "HOME",
            "street": "A" * 101,
            "city": "Test City",
            "pincode": "123456"
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_address_city_too_short(self):
        """POST /addresses with city < 2 characters should return 400."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "T",
            "pincode": "123456"
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_address_city_too_long(self):
        """POST /addresses with city > 50 characters should return 400."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "A" * 51,
            "pincode": "123456"
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_address_invalid_pincode_length(self):
        """POST /addresses with pincode != 6 digits should return 400."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "Test City",
            "pincode": "12345"  # 5 digits
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_address_pincode_with_letters(self):
        """POST /addresses with non-numeric pincode should return 400."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "Test City",
            "pincode": "12345a"
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_delete_nonexistent_address_returns_404(self):
        """DELETE /addresses/{id} for non-existent address should return 404."""
        response = requests.delete(f"{BASE_URL}/addresses/999999", headers=get_headers())
        assert response.status_code == 404

    # --- Bug Tests ---
    def test_bug_address_accepts_5_digit_pincode(self):
        """BUG: POST /addresses accepts pincode with 5 digits."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "TestCity",
            "pincode": "12345",
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts 5-digit pincode, got {response.status_code}"

    def test_bug_address_accepts_7_digit_pincode(self):
        """BUG: POST /addresses accepts pincode with 7 digits."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "TestCity",
            "pincode": "1234567",
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts 7-digit pincode, got {response.status_code}"

    def test_bug_address_accepts_non_digit_pincode(self):
        """BUG: POST /addresses accepts pincode with non-digit characters."""
        payload = {
            "label": "HOME",
            "street": "123 Test Street",
            "city": "TestCity",
            "pincode": "12345a",
            "is_default": False
        }
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts non-digit pincode, got {response.status_code}"


# =============================================================================
# PRODUCTS TESTS
# =============================================================================

class TestProducts:
    """Tests for Products endpoints."""

    def test_get_products_success(self):
        """GET /products should return list of products."""
        response = requests.get(f"{BASE_URL}/products", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_single_product_success(self):
        """GET /products/{id} for existing product should succeed."""
        product_id = get_valid_product_id()
        if product_id:
            response = requests.get(f"{BASE_URL}/products/{product_id}", headers=get_headers())
            assert response.status_code == 200
            data = response.json()
            assert "price" in data or "name" in data

    def test_get_nonexistent_product_returns_404(self):
        """GET /products/{id} for non-existent product should return 404."""
        response = requests.get(f"{BASE_URL}/products/999999", headers=get_headers())
        assert response.status_code == 404

    def test_products_filtered_by_category(self):
        """GET /products with category filter should work."""
        response = requests.get(f"{BASE_URL}/products?category=electronics", headers=get_headers())
        assert response.status_code == 200

    def test_products_searched_by_name(self):
        """GET /products with name search should work."""
        response = requests.get(f"{BASE_URL}/products?search=test", headers=get_headers())
        assert response.status_code == 200

    def test_products_sorted_by_price_asc(self):
        """GET /products sorted by price ascending should work."""
        response = requests.get(f"{BASE_URL}/products?sort=price_asc", headers=get_headers())
        assert response.status_code == 200

    def test_products_sorted_by_price_desc(self):
        """GET /products sorted by price descending should work."""
        response = requests.get(f"{BASE_URL}/products?sort=price_desc", headers=get_headers())
        assert response.status_code == 200


# =============================================================================
# CART TESTS
# =============================================================================

class TestCart:
    """Tests for Cart endpoints."""

    def setup_method(self):
        """Clear cart before each test."""
        clear_cart()
        remove_coupon()

    def test_get_cart_success(self):
        """GET /cart should return cart data."""
        response = get_cart()
        assert response.status_code == 200

    def test_add_valid_item_to_cart(self):
        """POST /cart/add with valid data should succeed."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            response = add_to_cart(product_id, 1)
            assert response.status_code == 200

    def test_add_item_quantity_zero_returns_400(self):
        """POST /cart/add with quantity=0 should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            response = add_to_cart(product_id, 0)
            assert response.status_code == 400

    def test_add_item_quantity_negative_returns_400(self):
        """POST /cart/add with negative quantity should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            response = add_to_cart(product_id, -1)
            assert response.status_code == 400

    def test_add_nonexistent_product_returns_404(self):
        """POST /cart/add with non-existent product should return 404."""
        response = add_to_cart(999999, 1)
        assert response.status_code == 404

    def test_add_same_product_twice_accumulates_quantity(self):
        """Adding same product twice should accumulate quantity."""
        product = get_product_with_stock()
        if product and product.get("stock", 0) >= 2:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)
            add_to_cart(product_id, 1)

            cart_response = get_cart()
            assert cart_response.status_code == 200
            cart_data = cart_response.json()

            items = cart_data.get("items", cart_data.get("cart_items", []))
            for item in items:
                item_product_id = item.get("product_id") or item.get("id")
                if item_product_id == product_id:
                    assert item.get("quantity", 0) == 2
                    break

    def test_add_item_exceeding_stock_returns_400(self):
        """POST /cart/add with quantity > stock should return 400."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            stock = product.get("stock", 0)
            response = add_to_cart(product_id, stock + 100)
            assert response.status_code == 400

    def test_cart_subtotal_calculation(self):
        """Cart item subtotal should be quantity * unit price."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            unit_price = product.get("price", 0)
            quantity = 2

            if product.get("stock", 0) >= quantity:
                add_to_cart(product_id, quantity)

                cart_response = get_cart()
                cart_data = cart_response.json()

                items = cart_data.get("items", cart_data.get("cart_items", []))
                for item in items:
                    item_product_id = item.get("product_id") or item.get("id")
                    if item_product_id == product_id:
                        subtotal = item.get("subtotal", 0)
                        expected = quantity * unit_price
                        assert subtotal == expected, f"Expected subtotal {expected}, got {subtotal}"
                        break

    def test_cart_total_is_sum_of_subtotals(self):
        """Cart total should be sum of all subtotals."""
        products = get_products()
        if isinstance(products, dict):
            products = products.get("products", [])

        products_with_stock = [p for p in products if p.get("stock", 0) >= 1][:2]

        if len(products_with_stock) >= 2:
            expected_total = 0
            for product in products_with_stock:
                product_id = product.get("product_id") or product.get("id")
                unit_price = product.get("price", 0)
                add_to_cart(product_id, 1)
                expected_total += unit_price

            cart_response = get_cart()
            cart_data = cart_response.json()
            actual_total = cart_data.get("total", 0)

            assert actual_total == expected_total, f"Expected total {expected_total}, got {actual_total}"

    def test_update_cart_item_valid(self):
        """POST /cart/update with valid quantity should succeed."""
        product = get_product_with_stock()
        if product and product.get("stock", 0) >= 2:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)

            payload = {"product_id": product_id, "quantity": 2}
            response = requests.post(f"{BASE_URL}/cart/update", json=payload, headers=get_headers())
            assert response.status_code == 200

    def test_update_cart_item_quantity_zero_returns_400(self):
        """POST /cart/update with quantity=0 should return 400."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)

            payload = {"product_id": product_id, "quantity": 0}
            response = requests.post(f"{BASE_URL}/cart/update", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_remove_item_from_cart(self):
        """POST /cart/remove should remove item from cart."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)

            payload = {"product_id": product_id}
            response = requests.post(f"{BASE_URL}/cart/remove", json=payload, headers=get_headers())
            assert response.status_code == 200

    def test_remove_nonexistent_item_returns_404(self):
        """POST /cart/remove for item not in cart should return 404."""
        payload = {"product_id": 999999}
        response = requests.post(f"{BASE_URL}/cart/remove", json=payload, headers=get_headers())
        assert response.status_code == 404

    def test_clear_cart_success(self):
        """DELETE /cart/clear should clear the cart."""
        response = clear_cart()
        assert response.status_code == 200

    # --- Bug Tests ---
    def test_bug_cart_accepts_zero_quantity(self):
        """BUG: POST /cart/add accepts quantity of 0."""
        response = add_to_cart(1, 0)
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts quantity=0, got {response.status_code}"

    def test_bug_cart_accepts_negative_quantity(self):
        """BUG: POST /cart/add accepts negative quantity."""
        response = add_to_cart(1, -1)
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts negative quantity, got {response.status_code}"

    def test_bug_cart_subtotal_incorrect(self):
        """BUG: Cart subtotal calculation is incorrect."""
        clear_cart()
        add_to_cart(1, 2)

        cart_response = get_cart()
        cart_data = cart_response.json()

        product_response = requests.get(f"{BASE_URL}/products/1", headers=get_headers())
        product_price = product_response.json().get("price", 0)

        if cart_data.get("items"):
            item = cart_data["items"][0]
            expected_subtotal = 2 * product_price
            actual_subtotal = item.get("subtotal", 0)
            assert actual_subtotal == expected_subtotal, f"BUG: Expected subtotal {expected_subtotal}, got {actual_subtotal}"

    def test_bug_cart_total_incorrect(self):
        """BUG: Cart total calculation is incorrect."""
        clear_cart()
        add_to_cart(1, 1)
        add_to_cart(2, 1)

        cart_response = get_cart()
        cart_data = cart_response.json()

        product1 = requests.get(f"{BASE_URL}/products/1", headers=get_headers()).json()
        product2 = requests.get(f"{BASE_URL}/products/2", headers=get_headers()).json()

        expected_total = product1.get("price", 0) + product2.get("price", 0)
        actual_total = cart_data.get("total", 0)
        assert actual_total == expected_total, f"BUG: Expected total {expected_total}, got {actual_total}"


# =============================================================================
# COUPON TESTS
# =============================================================================

class TestCoupons:
    """Tests for Coupon endpoints."""

    def setup_method(self):
        """Clear cart and remove coupons before each test."""
        clear_cart()
        remove_coupon()

    def test_apply_invalid_coupon_returns_error(self):
        """POST /coupon/apply with invalid code should return error."""
        payload = {"code": "INVALIDCODE123"}
        response = requests.post(f"{BASE_URL}/coupon/apply", json=payload, headers=get_headers())
        assert response.status_code in [400, 404]

    def test_apply_coupon_to_empty_cart(self):
        """Applying coupon to empty cart might fail min cart value check."""
        coupons_response = get_admin_coupons()
        if coupons_response.status_code == 200:
            coupons = coupons_response.json()
            if isinstance(coupons, list) and len(coupons) > 0:
                code = coupons[0].get("code")
                if code:
                    payload = {"code": code}
                    response = requests.post(f"{BASE_URL}/coupon/apply", json=payload, headers=get_headers())
                    # Should fail because cart is empty (min cart value not met)
                    assert response.status_code in [200, 400]

    def test_remove_coupon_success(self):
        """POST /coupon/remove should succeed."""
        response = remove_coupon()
        assert response.status_code == 200

    def test_coupon_min_cart_value_not_met(self):
        """Coupon should fail if cart total < min cart value."""
        coupons_response = get_admin_coupons()
        if coupons_response.status_code == 200:
            coupons = coupons_response.json()
            if isinstance(coupons, list):
                # Find a coupon with high min_cart_value
                for coupon in coupons:
                    min_value = coupon.get("min_cart_value", 0)
                    if min_value > 0:
                        code = coupon.get("code")
                        # Add a cheap item
                        product = get_product_with_stock()
                        if product:
                            product_id = product.get("product_id") or product.get("id")
                            price = product.get("price", 0)
                            if price < min_value:
                                add_to_cart(product_id, 1)
                                payload = {"code": code}
                                response = requests.post(f"{BASE_URL}/coupon/apply", json=payload, headers=get_headers())
                                # Should fail due to min cart value not met
                                if price < min_value:
                                    assert response.status_code == 400
                        break


# =============================================================================
# CHECKOUT TESTS
# =============================================================================

class TestCheckout:
    """Tests for Checkout endpoint."""

    def setup_method(self):
        """Clear cart before each test."""
        clear_cart()
        remove_coupon()

    def test_checkout_empty_cart_returns_400(self):
        """POST /checkout with empty cart should return 400."""
        payload = {"payment_method": "COD"}
        response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_checkout_invalid_payment_method_returns_400(self):
        """POST /checkout with invalid payment method should return 400."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)

            payload = {"payment_method": "BITCOIN"}
            response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_checkout_cod_valid(self):
        """POST /checkout with COD should succeed for small orders."""
        products = get_products()
        if isinstance(products, dict):
            products = products.get("products", [])

        # Find a cheap product (total < 5000)
        cheap_product = None
        for product in products:
            if product.get("stock", 0) > 0 and product.get("price", 0) < 4000:
                cheap_product = product
                break

        if cheap_product:
            product_id = cheap_product.get("product_id") or cheap_product.get("id")
            add_to_cart(product_id, 1)

            payload = {"payment_method": "COD"}
            response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
            # COD should work for orders < 5000
            if cheap_product.get("price", 0) * 1.05 <= 5000:
                assert response.status_code == 200

    def test_checkout_cod_over_5000_returns_400(self):
        """POST /checkout with COD for total > 5000 should return 400."""
        products = get_products()
        if isinstance(products, dict):
            products = products.get("products", [])

        # Find expensive product(s) to get total > 5000
        total_added = 0
        for product in products:
            if product.get("stock", 0) > 0:
                product_id = product.get("product_id") or product.get("id")
                price = product.get("price", 0)
                stock = product.get("stock", 0)

                # Calculate quantity needed
                qty_needed = min(stock, max(1, int((5500 - total_added) / price) + 1))
                if qty_needed > 0:
                    add_to_cart(product_id, qty_needed)
                    total_added += price * qty_needed

                if total_added > 5000:
                    break

        if total_added > 5000:
            payload = {"payment_method": "COD"}
            response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_checkout_wallet_valid(self):
        """POST /checkout with WALLET should succeed with sufficient balance."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            price = product.get("price", 0)

            # Add money to wallet
            add_amount = max(price * 2, 1000)
            requests.post(f"{BASE_URL}/wallet/add", json={"amount": add_amount}, headers=get_headers())

            add_to_cart(product_id, 1)

            payload = {"payment_method": "WALLET"}
            response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
            assert response.status_code in [200, 400]  # 400 if insufficient balance

    def test_checkout_card_valid(self):
        """POST /checkout with CARD should succeed."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)

            payload = {"payment_method": "CARD"}
            response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
            assert response.status_code == 200

    def test_checkout_gst_applied_once(self):
        """GST should be applied exactly once (5%)."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            price = product.get("price", 0)
            add_to_cart(product_id, 1)

            # Get cart total before checkout
            cart_response = get_cart()
            cart_data = cart_response.json()
            cart_total = cart_data.get("total", 0)

            payload = {"payment_method": "CARD"}
            response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())

            if response.status_code == 200:
                order_data = response.json()
                order_total = order_data.get("total", order_data.get("order", {}).get("total", 0))

                # Total should be cart_total + 5% GST
                expected_total = cart_total * 1.05
                assert abs(order_total - expected_total) < 1, f"GST calculation error: expected {expected_total}, got {order_total}"

    # --- Bug Tests ---
    def test_bug_checkout_accepts_empty_cart(self):
        """BUG: POST /checkout accepts empty cart."""
        clear_cart()
        payload = {"payment_method": "COD"}
        response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts empty cart checkout, got {response.status_code}"

    def test_bug_cod_payment_status_is_paid(self):
        """BUG: COD checkout returns payment_status as PAID instead of PENDING."""
        clear_cart()
        add_to_cart(1, 1)
        payload = {"payment_method": "COD"}
        response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
        if response.status_code == 200:
            data = response.json()
            status = data.get("payment_status", "")
            assert status == "PENDING", f"BUG: COD payment_status should be PENDING, got {status}"

    def test_bug_wallet_payment_status_is_paid(self):
        """BUG: WALLET checkout returns payment_status as PAID instead of PENDING."""
        clear_cart()
        add_to_cart(1, 1)
        requests.post(f"{BASE_URL}/wallet/add", json={"amount": 10000}, headers=get_headers())
        payload = {"payment_method": "WALLET"}
        response = requests.post(f"{BASE_URL}/checkout", json=payload, headers=get_headers())
        if response.status_code == 200:
            data = response.json()
            status = data.get("payment_status", "")
            assert status == "PENDING", f"BUG: WALLET payment_status should be PENDING, got {status}"


# =============================================================================
# WALLET TESTS
# =============================================================================

class TestWallet:
    """Tests for Wallet endpoints."""

    def test_get_wallet_balance(self):
        """GET /wallet should return balance."""
        response = requests.get(f"{BASE_URL}/wallet", headers=get_headers())
        assert response.status_code == 200
        data = response.json()
        # API returns wallet_balance instead of balance
        assert "wallet_balance" in data or "balance" in data

    def test_add_wallet_amount_zero_returns_400(self):
        """POST /wallet/add with amount=0 should return 400."""
        payload = {"amount": 0}
        response = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_wallet_amount_negative_returns_400(self):
        """POST /wallet/add with negative amount should return 400."""
        payload = {"amount": -100}
        response = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_wallet_amount_over_100000_returns_400(self):
        """POST /wallet/add with amount > 100000 should return 400."""
        payload = {"amount": 100001}
        response = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_add_wallet_amount_boundary_max(self):
        """POST /wallet/add with amount=100000 should succeed."""
        payload = {"amount": 100000}
        response = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=get_headers())
        assert response.status_code == 200

    def test_add_wallet_amount_valid(self):
        """POST /wallet/add with valid amount should succeed."""
        payload = {"amount": 500}
        response = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=get_headers())
        assert response.status_code == 200

    def test_wallet_pay_exceeds_balance_returns_400(self):
        """POST /wallet/pay with amount > balance should return 400."""
        # Get current balance
        balance = get_wallet_balance()

        # Try to pay more than balance
        payload = {"amount": balance + 10000}
        response = requests.post(f"{BASE_URL}/wallet/pay", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_wallet_pay_zero_returns_400(self):
        """POST /wallet/pay with amount=0 should return 400."""
        payload = {"amount": 0}
        response = requests.post(f"{BASE_URL}/wallet/pay", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_wallet_pay_negative_returns_400(self):
        """POST /wallet/pay with negative amount should return 400."""
        payload = {"amount": -100}
        response = requests.post(f"{BASE_URL}/wallet/pay", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_wallet_exact_deduction(self):
        """Wallet should deduct exactly the requested amount."""
        # Add some money first
        requests.post(f"{BASE_URL}/wallet/add", json={"amount": 1000}, headers=get_headers())

        initial_balance = get_wallet_balance()
        pay_amount = 100

        if initial_balance >= pay_amount:
            response = requests.post(f"{BASE_URL}/wallet/pay", json={"amount": pay_amount}, headers=get_headers())

            if response.status_code == 200:
                new_balance = get_wallet_balance()
                expected_balance = initial_balance - pay_amount
                assert new_balance == expected_balance, f"Expected {expected_balance}, got {new_balance}"

    # --- Bug Tests ---
    def test_bug_wallet_pay_exceeds_balance(self):
        """BUG: POST /wallet/pay allows paying more than balance."""
        balance = get_wallet_balance()
        payload = {"amount": balance + 100000}
        response = requests.post(f"{BASE_URL}/wallet/pay", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API allows paying more than balance, got {response.status_code}"

    def test_bug_wallet_precision_error(self):
        """BUG: Wallet balance calculation has floating-point precision errors."""
        initial = get_wallet_balance()
        requests.post(f"{BASE_URL}/wallet/add", json={"amount": 100}, headers=get_headers())
        after_add = get_wallet_balance()
        requests.post(f"{BASE_URL}/wallet/pay", json={"amount": 50}, headers=get_headers())
        after_pay = get_wallet_balance()
        expected = initial + 100 - 50
        assert abs(after_pay - expected) < 0.01, f"BUG: Expected balance {expected}, got {after_pay}"


# =============================================================================
# LOYALTY TESTS
# =============================================================================

class TestLoyalty:
    """Tests for Loyalty Points endpoints."""

    def test_get_loyalty_points(self):
        """GET /loyalty should return points."""
        response = requests.get(f"{BASE_URL}/loyalty", headers=get_headers())
        assert response.status_code == 200

    def test_redeem_zero_points_returns_400(self):
        """POST /loyalty/redeem with amount=0 should return 400."""
        payload = {"amount": 0}
        response = requests.post(f"{BASE_URL}/loyalty/redeem", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_redeem_negative_points_returns_400(self):
        """POST /loyalty/redeem with negative amount should return 400."""
        payload = {"amount": -10}
        response = requests.post(f"{BASE_URL}/loyalty/redeem", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_redeem_more_than_available_returns_400(self):
        """POST /loyalty/redeem with amount > available should return 400."""
        response = requests.get(f"{BASE_URL}/loyalty", headers=get_headers())
        if response.status_code == 200:
            points = response.json().get("points", 0)
            payload = {"amount": points + 1000}
            redeem_response = requests.post(f"{BASE_URL}/loyalty/redeem", json=payload, headers=get_headers())
            assert redeem_response.status_code == 400


# =============================================================================
# ORDERS TESTS
# =============================================================================

class TestOrders:
    """Tests for Orders endpoints."""

    def test_get_orders_success(self):
        """GET /orders should return orders list."""
        response = get_orders()
        assert response.status_code == 200

    def test_get_nonexistent_order_returns_404(self):
        """GET /orders/{id} for non-existent order should return 404."""
        response = requests.get(f"{BASE_URL}/orders/999999", headers=get_headers())
        assert response.status_code == 404

    def test_cancel_nonexistent_order_returns_404(self):
        """POST /orders/{id}/cancel for non-existent order should return 404."""
        response = requests.post(f"{BASE_URL}/orders/999999/cancel", headers=get_headers())
        assert response.status_code == 404

    def test_cancel_delivered_order_returns_400(self):
        """POST /orders/{id}/cancel for delivered order should return 400."""
        # Get user's own orders and find a delivered one
        orders_response = requests.get(f"{BASE_URL}/orders", headers=get_headers())
        if orders_response.status_code == 200:
            orders = orders_response.json()
            if isinstance(orders, list):
                delivered_order = next((o for o in orders if o.get("order_status") == "DELIVERED"), None)
                if delivered_order:
                    order_id = delivered_order.get("order_id")
                    response = requests.post(f"{BASE_URL}/orders/{order_id}/cancel", headers=get_headers())
                    assert response.status_code == 400

    def test_order_invoice_shows_correct_totals(self):
        """GET /orders/{id}/invoice should show correct totals."""
        orders_response = get_orders()
        if orders_response.status_code == 200:
            orders = orders_response.json()
            if isinstance(orders, list) and len(orders) > 0:
                order_id = orders[0].get("order_id") or orders[0].get("id")
                response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=get_headers())
                if response.status_code == 200:
                    invoice = response.json()
                    subtotal = invoice.get("subtotal", 0)
                    gst = invoice.get("gst", invoice.get("gst_amount", 0))
                    total = invoice.get("total", 0)

                    # Verify GST is 5% of subtotal
                    expected_gst = subtotal * 0.05
                    assert abs(gst - expected_gst) < 1, f"GST mismatch: expected {expected_gst}, got {gst}"

                    # Verify total = subtotal + gst
                    expected_total = subtotal + gst
                    assert abs(total - expected_total) < 1, f"Total mismatch: expected {expected_total}, got {total}"

    def test_cancel_order_restores_stock(self):
        """Cancelling order should restore product stock."""
        clear_cart()
        product = get_product_with_stock()

        if product:
            product_id = product.get("product_id") or product.get("id")
            initial_stock = product.get("stock", 0)

            if initial_stock >= 1:
                # Add to cart and checkout
                add_to_cart(product_id, 1)
                checkout_response = requests.post(
                    f"{BASE_URL}/checkout",
                    json={"payment_method": "CARD"},
                    headers=get_headers()
                )

                if checkout_response.status_code == 200:
                    order_data = checkout_response.json()
                    order_id = order_data.get("order_id") or order_data.get("order", {}).get("order_id")

                    if order_id:
                        # Get stock after checkout
                        product_response = requests.get(f"{BASE_URL}/products/{product_id}", headers=get_headers())
                        stock_after_checkout = product_response.json().get("stock", 0)

                        # Cancel order
                        cancel_response = requests.post(f"{BASE_URL}/orders/{order_id}/cancel", headers=get_headers())

                        if cancel_response.status_code == 200:
                            # Check stock restored
                            product_response = requests.get(f"{BASE_URL}/products/{product_id}", headers=get_headers())
                            stock_after_cancel = product_response.json().get("stock", 0)

                            assert stock_after_cancel == stock_after_checkout + 1

    # --- Bug Tests ---
    def test_bug_cancel_delivered_order(self):
        """BUG: POST /orders/{id}/cancel accepts delivered orders."""
        orders_response = requests.get(f"{BASE_URL}/orders", headers=get_headers())
        if orders_response.status_code == 200:
            orders = orders_response.json()
            delivered_order = next((o for o in orders if o.get("order_status") == "DELIVERED"), None)
            if delivered_order:
                order_id = delivered_order.get("order_id")
                response = requests.post(f"{BASE_URL}/orders/{order_id}/cancel", headers=get_headers())
                # Expected: 400, Actual: 200
                assert response.status_code == 400, f"BUG: API allows cancelling delivered orders, got {response.status_code}"

    def test_bug_invoice_gst_calculation(self):
        """BUG: Order invoice GST calculation is incorrect."""
        orders_response = requests.get(f"{BASE_URL}/orders", headers=get_headers())
        if orders_response.status_code == 200:
            orders = orders_response.json()
            if orders:
                order_id = orders[0].get("order_id")
                response = requests.get(f"{BASE_URL}/orders/{order_id}/invoice", headers=get_headers())
                if response.status_code == 200:
                    invoice = response.json()
                    subtotal = invoice.get("subtotal", 0)
                    gst = invoice.get("gst", invoice.get("gst_amount", 0))
                    expected_gst = subtotal * 0.05
                    assert abs(gst - expected_gst) < 0.1, f"BUG: Expected GST {expected_gst}, got {gst}"


# =============================================================================
# REVIEWS TESTS
# =============================================================================

class TestReviews:
    """Tests for Reviews endpoints."""

    def test_get_product_reviews(self):
        """GET /products/{id}/reviews should return reviews."""
        product_id = get_valid_product_id()
        if product_id:
            response = requests.get(f"{BASE_URL}/products/{product_id}/reviews", headers=get_headers())
            assert response.status_code == 200

    def test_add_review_valid(self):
        """POST /products/{id}/reviews with valid data should succeed."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 4, "comment": "Great product!"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code in [200, 201]

    def test_add_review_rating_zero_returns_400(self):
        """POST /products/{id}/reviews with rating=0 should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 0, "comment": "Test comment"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_add_review_rating_six_returns_400(self):
        """POST /products/{id}/reviews with rating=6 should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 6, "comment": "Test comment"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_add_review_rating_negative_returns_400(self):
        """POST /products/{id}/reviews with negative rating should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": -1, "comment": "Test comment"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_add_review_rating_boundary_min(self):
        """POST /products/{id}/reviews with rating=1 should succeed."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 1, "comment": "Boundary test min"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code in [200, 201]

    def test_add_review_rating_boundary_max(self):
        """POST /products/{id}/reviews with rating=5 should succeed."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 5, "comment": "Boundary test max"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code in [200, 201]

    def test_add_review_comment_empty_returns_400(self):
        """POST /products/{id}/reviews with empty comment should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 3, "comment": ""}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_add_review_comment_too_long_returns_400(self):
        """POST /products/{id}/reviews with comment > 200 chars should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 3, "comment": "A" * 201}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_add_review_comment_boundary_max(self):
        """POST /products/{id}/reviews with comment = 200 chars should succeed."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 3, "comment": "A" * 200}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code in [200, 201]

    # --- Bug Tests ---
    def test_bug_review_accepts_zero_rating(self):
        """BUG: POST reviews accepts rating=0."""
        payload = {"rating": 0, "comment": "Test comment"}
        response = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts rating=0, got {response.status_code}"

    def test_bug_review_accepts_rating_above_5(self):
        """BUG: POST reviews accepts rating=6."""
        payload = {"rating": 6, "comment": "Test comment"}
        response = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts rating=6, got {response.status_code}"

    def test_bug_review_accepts_missing_rating(self):
        """BUG: POST reviews accepts missing rating."""
        payload = {"comment": "Test comment"}
        response = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts missing rating, got {response.status_code}"

    def test_bug_review_accepts_null_rating(self):
        """BUG: POST reviews accepts null rating."""
        payload = {"rating": None, "comment": "Test comment"}
        response = requests.post(f"{BASE_URL}/products/1/reviews", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: API accepts null rating, got {response.status_code}"

    def test_bug_review_nonexistent_product(self):
        """BUG: API accepts reviews for nonexistent products."""
        payload = {"rating": 4, "comment": "Test"}
        response = requests.post(f"{BASE_URL}/products/999999/reviews", json=payload, headers=get_headers())
        # Expected: 404, Actual: 200
        assert response.status_code == 404, f"BUG: API accepts review for nonexistent product, got {response.status_code}"

    def test_bug_average_rating_rounded(self):
        """BUG: API rounds off average rating to nearest integer."""
        response = requests.get(f"{BASE_URL}/products/1/reviews", headers=get_headers())
        if response.status_code == 200:
            data = response.json()
            avg = data.get("average_rating", 0)
            if avg != 0 and avg != int(avg):
                # If it's already a float with decimals, no bug
                pass
            elif avg != 0:
                # If it's exactly an integer, might be a bug (rounded)
                assert isinstance(avg, float), f"BUG: Average rating is rounded integer {avg}"


# =============================================================================
# SUPPORT TICKETS TESTS
# =============================================================================

class TestSupportTickets:
    """Tests for Support Tickets endpoints."""

    def test_get_tickets_success(self):
        """GET /support/tickets should return tickets list."""
        response = requests.get(f"{BASE_URL}/support/tickets", headers=get_headers())
        assert response.status_code == 200

    def test_create_ticket_valid(self):
        """POST /support/ticket with valid data should succeed."""
        payload = {"subject": "Test Issue", "message": "This is a test message."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]

    def test_create_ticket_subject_too_short_returns_400(self):
        """POST /support/ticket with subject < 5 chars should return 400."""
        payload = {"subject": "Hi", "message": "This is a test message."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_create_ticket_subject_too_long_returns_400(self):
        """POST /support/ticket with subject > 100 chars should return 400."""
        payload = {"subject": "A" * 101, "message": "This is a test message."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_create_ticket_subject_boundary_min(self):
        """POST /support/ticket with subject = 5 chars should succeed."""
        payload = {"subject": "Hello", "message": "This is a test message."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]

    def test_create_ticket_subject_boundary_max(self):
        """POST /support/ticket with subject = 100 chars should succeed."""
        payload = {"subject": "A" * 100, "message": "This is a test message."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]

    def test_create_ticket_message_empty_returns_400(self):
        """POST /support/ticket with empty message should return 400."""
        payload = {"subject": "Test Issue", "message": ""}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_create_ticket_message_too_long_returns_400(self):
        """POST /support/ticket with message > 500 chars should return 400."""
        payload = {"subject": "Test Issue", "message": "A" * 501}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_create_ticket_message_boundary_max(self):
        """POST /support/ticket with message = 500 chars should succeed."""
        payload = {"subject": "Test Issue", "message": "A" * 500}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code in [200, 201]

    def test_ticket_starts_with_open_status(self):
        """New ticket should have status OPEN."""
        payload = {"subject": "Status Test", "message": "Testing initial status."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        if response.status_code in [200, 201]:
            data = response.json()
            ticket = data.get("ticket", data)
            assert ticket.get("status") == "OPEN"

    def test_update_ticket_status_open_to_in_progress(self):
        """Ticket status can change from OPEN to IN_PROGRESS."""
        # Create a ticket first
        payload = {"subject": "Update Test", "message": "Testing status update."}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())

        if response.status_code in [200, 201]:
            data = response.json()
            ticket = data.get("ticket", data)
            ticket_id = ticket.get("ticket_id") or ticket.get("id")

            if ticket_id:
                update_payload = {"status": "IN_PROGRESS"}
                update_response = requests.put(
                    f"{BASE_URL}/support/tickets/{ticket_id}",
                    json=update_payload,
                    headers=get_headers()
                )
                assert update_response.status_code == 200

    def test_update_ticket_invalid_status_transition(self):
        """Ticket status cannot go backwards (CLOSED to OPEN)."""
        # Get existing tickets
        response = requests.get(f"{BASE_URL}/support/tickets", headers=get_headers())
        if response.status_code == 200:
            tickets = response.json()
            if isinstance(tickets, list):
                for ticket in tickets:
                    if ticket.get("status") == "CLOSED":
                        ticket_id = ticket.get("ticket_id") or ticket.get("id")
                        update_payload = {"status": "OPEN"}
                        update_response = requests.put(
                            f"{BASE_URL}/support/tickets/{ticket_id}",
                            json=update_payload,
                            headers=get_headers()
                        )
                        assert update_response.status_code == 400
                        break

    # --- Bug Tests ---
    def test_bug_ticket_open_to_closed_directly(self):
        """BUG: API allows changing ticket status from OPEN to CLOSED directly."""
        payload = {"subject": "Bug Test Ticket", "message": "Testing direct close."}
        create_response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        if create_response.status_code in [200, 201]:
            tickets = requests.get(f"{BASE_URL}/support/tickets", headers=get_headers()).json()
            open_ticket = next((t for t in tickets if t.get("status") == "OPEN"), None)
            if open_ticket:
                ticket_id = open_ticket.get("ticket_id")
                response = requests.put(
                    f"{BASE_URL}/support/tickets/{ticket_id}",
                    json={"status": "CLOSED"},
                    headers=get_headers()
                )
                # Expected: 400 (invalid transition), Actual: 200
                assert response.status_code == 400, f"BUG: API allows OPEN->CLOSED, got {response.status_code}"

    def test_bug_ticket_accepts_invalid_status(self):
        """BUG: API accepts invalid ticket status values."""
        tickets = requests.get(f"{BASE_URL}/support/tickets", headers=get_headers()).json()
        if tickets:
            ticket_id = tickets[0].get("ticket_id")
            response = requests.put(
                f"{BASE_URL}/support/tickets/{ticket_id}",
                json={"status": "INVALID_STATUS"},
                headers=get_headers()
            )
            # Expected: 400, Actual: 200
            assert response.status_code == 400, f"BUG: API accepts invalid status, got {response.status_code}"


# =============================================================================
# ADMIN ENDPOINT TESTS
# =============================================================================

class TestAdminEndpoints:
    """Tests for Admin endpoints."""

    def test_admin_get_users(self):
        """GET /admin/users should return all users."""
        response = requests.get(f"{BASE_URL}/admin/users", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_specific_user(self):
        """GET /admin/users/{id} should return user data."""
        response = requests.get(f"{BASE_URL}/admin/users/1", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_carts(self):
        """GET /admin/carts should return all carts."""
        response = requests.get(f"{BASE_URL}/admin/carts", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_orders(self):
        """GET /admin/orders should return all orders."""
        response = requests.get(f"{BASE_URL}/admin/orders", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_products(self):
        """GET /admin/products should return all products including inactive."""
        response = requests.get(f"{BASE_URL}/admin/products", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_coupons(self):
        """GET /admin/coupons should return all coupons."""
        response = requests.get(f"{BASE_URL}/admin/coupons", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_tickets(self):
        """GET /admin/tickets should return all tickets."""
        response = requests.get(f"{BASE_URL}/admin/tickets", headers=get_admin_headers())
        assert response.status_code == 200

    def test_admin_get_addresses(self):
        """GET /admin/addresses should return all addresses."""
        response = requests.get(f"{BASE_URL}/admin/addresses", headers=get_admin_headers())
        assert response.status_code == 200


# =============================================================================
# DATA TYPE VALIDATION TESTS
# =============================================================================

class TestDataTypes:
    """Tests for wrong data type handling."""

    def test_cart_add_string_quantity(self):
        """POST /cart/add with string quantity should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"product_id": product_id, "quantity": "five"}
            response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_cart_add_float_quantity(self):
        """POST /cart/add with float quantity should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"product_id": product_id, "quantity": 1.5}
            response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_wallet_add_string_amount(self):
        """POST /wallet/add with string amount should return 400."""
        payload = {"amount": "hundred"}
        response = requests.post(f"{BASE_URL}/wallet/add", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_review_rating_string(self):
        """POST /products/{id}/reviews with string rating should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": "five", "comment": "Test"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400


# =============================================================================
# MISSING FIELD TESTS
# =============================================================================

class TestMissingFields:
    """Tests for missing required fields."""

    def test_cart_add_missing_product_id(self):
        """POST /cart/add without product_id should return 400."""
        payload = {"quantity": 1}
        response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_cart_add_missing_quantity(self):
        """POST /cart/add without quantity should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"product_id": product_id}
            response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_checkout_missing_payment_method(self):
        """POST /checkout without payment_method should return 400."""
        clear_cart()
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            add_to_cart(product_id, 1)

            response = requests.post(f"{BASE_URL}/checkout", json={}, headers=get_headers())
            assert response.status_code == 400

    def test_address_missing_label(self):
        """POST /addresses without label should return 400."""
        payload = {"street": "123 Test St", "city": "Test City", "pincode": "123456"}
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_address_missing_street(self):
        """POST /addresses without street should return 400."""
        payload = {"label": "HOME", "city": "Test City", "pincode": "123456"}
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_address_missing_city(self):
        """POST /addresses without city should return 400."""
        payload = {"label": "HOME", "street": "123 Test St", "pincode": "123456"}
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_address_missing_pincode(self):
        """POST /addresses without pincode should return 400."""
        payload = {"label": "HOME", "street": "123 Test St", "city": "Test City"}
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_review_missing_rating(self):
        """POST reviews without rating should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"comment": "Test comment"}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_review_missing_comment(self):
        """POST reviews without comment should return 400."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"rating": 4}
            response = requests.post(f"{BASE_URL}/products/{product_id}/reviews", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_ticket_missing_subject(self):
        """POST /support/ticket without subject should return 400."""
        payload = {"message": "Test message content"}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_ticket_missing_message(self):
        """POST /support/ticket without message should return 400."""
        payload = {"subject": "Test Subject"}
        response = requests.post(f"{BASE_URL}/support/ticket", json=payload, headers=get_headers())
        assert response.status_code == 400

    def test_coupon_apply_missing_code(self):
        """POST /coupon/apply without code should return 400."""
        response = requests.post(f"{BASE_URL}/coupon/apply", json={}, headers=get_headers())
        assert response.status_code == 400

    # --- Bug Tests ---
    def test_bug_cart_add_no_product_id_returns_404(self):
        """BUG: POST /cart/add without product_id returns 404 instead of 400."""
        payload = {"quantity": 1}
        response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
        # Expected: 400, Actual: 404
        assert response.status_code == 400, f"BUG: Missing product_id returns {response.status_code}, expected 400"

    def test_bug_cart_add_no_quantity_accepted(self):
        """BUG: POST /cart/add without quantity is accepted."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"product_id": product_id}
            response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
            # Expected: 400, Actual: 200
            assert response.status_code == 400, f"BUG: Missing quantity returns {response.status_code}, expected 400"

    def test_bug_address_no_pincode_accepted(self):
        """BUG: POST /addresses without pincode is accepted."""
        payload = {"label": "HOME", "street": "123 Test Street", "city": "Test City"}
        response = requests.post(f"{BASE_URL}/addresses", json=payload, headers=get_headers())
        # Expected: 400, Actual: 200
        assert response.status_code == 400, f"BUG: Missing pincode returns {response.status_code}, expected 400"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and potential bugs."""

    def setup_method(self):
        """Clear cart before each test."""
        clear_cart()
        remove_coupon()

    def test_empty_json_body(self):
        """Sending empty JSON body should be handled gracefully."""
        response = requests.post(f"{BASE_URL}/cart/add", json={}, headers=get_headers())
        assert response.status_code == 400

    def test_null_values_in_payload(self):
        """Null values in payload should be handled."""
        payload = {"product_id": None, "quantity": None}
        response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
        assert response.status_code in [400, 404]

    def test_very_large_quantity(self):
        """Very large quantity should be rejected."""
        product_id = get_valid_product_id()
        if product_id:
            payload = {"product_id": product_id, "quantity": 999999999}
            response = requests.post(f"{BASE_URL}/cart/add", json=payload, headers=get_headers())
            assert response.status_code == 400

    def test_special_characters_in_search(self):
        """Special characters in product search should be handled."""
        response = requests.get(f"{BASE_URL}/products?search=<script>alert(1)</script>", headers=get_headers())
        assert response.status_code == 200

    def test_sql_injection_attempt_in_search(self):
        """SQL injection in search should be handled safely."""
        response = requests.get(f"{BASE_URL}/products?search='; DROP TABLE products; --", headers=get_headers())
        assert response.status_code == 200

    def test_checkout_with_coupon_discount_calculation(self):
        """Coupon discount should be calculated correctly."""
        product = get_product_with_stock()
        if product:
            product_id = product.get("product_id") or product.get("id")
            price = product.get("price", 0)
            add_to_cart(product_id, 1)

            coupons_response = get_admin_coupons()
            if coupons_response.status_code == 200:
                coupons = coupons_response.json()
                if isinstance(coupons, list):
                    for coupon in coupons:
                        min_value = coupon.get("min_cart_value", 0)
                        if price >= min_value and not coupon.get("is_expired", True):
                            code = coupon.get("code")
                            discount_type = coupon.get("discount_type")
                            discount_value = coupon.get("discount_value", 0)
                            max_discount = coupon.get("max_discount", float('inf'))

                            apply_response = requests.post(
                                f"{BASE_URL}/coupon/apply",
                                json={"code": code},
                                headers=get_headers()
                            )

                            if apply_response.status_code == 200:
                                cart_response = get_cart()
                                cart_data = cart_response.json()
                                discount_applied = cart_data.get("discount", 0)

                                # Verify discount calculation
                                if discount_type == "PERCENT":
                                    expected_discount = min(price * discount_value / 100, max_discount)
                                else:
                                    expected_discount = min(discount_value, max_discount)

                                assert abs(discount_applied - expected_discount) < 1
                            break

    # --- Bug Tests ---
    def test_bug_empty_json_returns_404(self):
        """BUG: Empty JSON to /cart/add returns 404 instead of 400."""
        response = requests.post(f"{BASE_URL}/cart/add", json={}, headers=get_headers())
        # Expected: 400, Actual: 404
        assert response.status_code == 400, f"BUG: Empty JSON returns {response.status_code}, expected 400"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
