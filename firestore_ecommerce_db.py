"""
Complete Firestore E-commerce Database Operations
Firebase Firestore Python SDK implementation for e-commerce platform

Collections: users, products, orders, categories, inventory, warehouses, 
            carts, reviews, notifications, suppliers

Author: Generated for Firebase Firestore E-commerce Platform
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import NotFound, InvalidArgument
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirestoreEcommerceDB:
    """
    Main class for Firestore e-commerce database operations
    """
    
    def __init__(self, project_id: str = None):
        """Initialize Firestore client using Firebase Admin SDK"""
        try:
            # Use the already initialized Firebase Admin SDK
            from firebase_admin import firestore as admin_firestore
            self.db = admin_firestore.client()
            logger.info("Firestore client initialized successfully using Firebase Admin SDK")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore client: {e}")
            raise

    def _handle_error(self, operation: str, error: Exception) -> Dict[str, Any]:
        """Centralized error handling"""
        logger.error(f"Error in {operation}: {str(error)}")
        return {
            'success': False,
            'error': str(error),
            'operation': operation,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _success_response(self, data: Any = None, message: str = "Operation successful") -> Dict[str, Any]:
        """Standardized success response format"""
        return {
            'success': True,
            'data': data,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }

    def _optimize_query_with_index(self, collection_name: str, filters: List[Tuple], order_by: List[Tuple] = None) -> firestore.Query:
        """
        Create optimized Firestore query with proper indexing and performance monitoring
        
        Args:
            collection_name: Name of the collection
            filters: List of (field, operator, value) tuples
            order_by: List of (field, direction) tuples
        
        Returns:
            Optimized Firestore query
        """
        query = self.db.collection(collection_name)
        
        # Apply filters in optimal order for Firestore indexing
        # Order: equality filters, range filters, array filters, ordering
        equality_filters = []
        range_filters = []
        array_filters = []
        in_filters = []
        
        for field, operator, value in filters:
            if operator == '==':
                equality_filters.append((field, operator, value))
            elif operator in ['<', '<=', '>', '>=', '!=']:
                range_filters.append((field, operator, value))
            elif operator in ['array-contains', 'array-contains-any']:
                array_filters.append((field, operator, value))
            elif operator in ['in', 'not-in']:
                in_filters.append((field, operator, value))
            else:
                # Default to equality for unknown operators
                equality_filters.append((field, operator, value))
        
        # Apply filters in optimal order for composite indexes
        # 1. Equality filters first (best for composite indexes)
        for field, operator, value in equality_filters:
            query = query.where(filter=FieldFilter(field, operator, value))
        
        # 2. IN filters (treated as equality by Firestore)
        for field, operator, value in in_filters:
            query = query.where(filter=FieldFilter(field, operator, value))
        
        # 3. Range filters (only one range filter per query allowed)
        if range_filters:
            # Use only the first range filter to avoid index conflicts
            field, operator, value = range_filters[0]
            query = query.where(filter=FieldFilter(field, operator, value))
            
            if len(range_filters) > 1:
                logger.warning(f"Multiple range filters detected for {collection_name}. Only using first one: {field} {operator}")
        
        # 4. Array filters last (most expensive)
        for field, operator, value in array_filters:
            query = query.where(filter=FieldFilter(field, operator, value))
        
        # 5. Apply ordering (must match index field order)
        if order_by:
            for field, direction in order_by:
                query = query.order_by(field, direction=direction)
        
        return query

    def _paginate_query(self, query: firestore.Query, limit: int, last_doc_id: str = None) -> Tuple[firestore.Query, bool]:
        """
        Add pagination to query with cursor-based approach and performance optimization
        
        Args:
            query: Base Firestore query
            limit: Number of documents to return
            last_doc_id: ID of last document from previous page
        
        Returns:
            Tuple of (paginated_query, has_cursor)
        """
        # Optimize limit for better performance
        effective_limit = min(limit + 1, 100)  # Cap at 100 to prevent large queries
        paginated_query = query.limit(effective_limit)
        
        if last_doc_id:
            try:
                # Get the collection name from the query
                collection_name = query._parent.id if hasattr(query, '_parent') else 'products'
                last_doc = self.db.collection(collection_name).document(last_doc_id).get()
                if last_doc.exists:
                    paginated_query = paginated_query.start_after(last_doc)
                    return paginated_query, True
            except Exception as e:
                logger.warning(f"Failed to use cursor pagination: {e}")
        
        return paginated_query, False

    def _execute_query_with_monitoring(self, query: firestore.Query, operation_name: str) -> Tuple[List[Any], float]:
        """
        Execute Firestore query with performance monitoring
        
        Args:
            query: Firestore query to execute
            operation_name: Name of the operation for logging
        
        Returns:
            Tuple of (results, execution_time_seconds)
        """
        start_time = datetime.utcnow()
        
        try:
            # Execute query
            docs = list(query.stream())
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Log performance metrics
            logger.info(f"Query '{operation_name}' executed in {execution_time:.3f}s, returned {len(docs)} documents")
            
            # Log warning for slow queries
            if execution_time > 2.0:
                logger.warning(f"Slow query detected: '{operation_name}' took {execution_time:.3f}s")
            
            return docs, execution_time
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Query '{operation_name}' failed after {execution_time:.3f}s: {str(e)}")
            raise e

    # ==================== USERS OPERATIONS ====================
    
    def create_user_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user profile in the users collection
        Security: Requires authentication, user can only create their own profile
        """
        try:
            user_id = user_data.get('user_id') or str(uuid.uuid4())
            
            # Add metadata
            user_data.update({
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True,
                'last_login': None
            })
            
            # Remove user_id from data if it exists (it's the document ID)
            user_data.pop('user_id', None)
            
            self.db.collection('users').document(user_id).set(user_data)
            
            logger.info(f"User profile created: {user_id}")
            return self._success_response({'user_id': user_id}, "User profile created successfully")
            
        except Exception as e:
            return self._handle_error("create_user_profile", e)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch a user profile by user ID
        Security: Users can only access their own profile unless admin
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                return self._handle_error("get_user_profile", Exception("User not found"))
            
            user_data = user_doc.to_dict()
            user_data['user_id'] = user_id
            
            return self._success_response(user_data)
            
        except Exception as e:
            return self._handle_error("get_user_profile", e)

    def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user profile (address/phone/preferences/etc)
        Security: Users can only update their own profile
        """
        try:
            # Add update timestamp
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update(update_data)
            
            logger.info(f"User profile updated: {user_id}")
            return self._success_response(message="User profile updated successfully")
            
        except NotFound:
            return self._handle_error("update_user_profile", Exception("User not found"))
        except Exception as e:
            return self._handle_error("update_user_profile", e)

    def get_users_by_role(self, role: str, limit: int = 50, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch all users with a specific role (paginated)
        Security: Admin only
        """
        try:
            query = self.db.collection('users').where(filter=FieldFilter('role', '==', role)).limit(limit)
            
            if last_doc_id:
                last_doc = self.db.collection('users').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            users = []
            last_doc = None
            
            for doc in docs:
                user_data = doc.to_dict()
                user_data['user_id'] = doc.id
                users.append(user_data)
                last_doc = doc
            
            return self._success_response({
                'users': users,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(users) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_users_by_role", e)

    def deactivate_user(self, user_id: str) -> Dict[str, Any]:
        """
        Deactivate/soft delete a user
        Security: Admin only
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                'is_active': False,
                'deactivated_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"User deactivated: {user_id}")
            return self._success_response(message="User deactivated successfully")
            
        except NotFound:
            return self._handle_error("deactivate_user", Exception("User not found"))
        except Exception as e:
            return self._handle_error("deactivate_user", e)

    # ==================== PRODUCTS OPERATIONS ====================
    
    def add_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new product with all fields including inventory, images, and pricing
        Security: Sellers can add products, admin can add any product
        """
        try:
            product_id = str(uuid.uuid4())
            
            # Add metadata
            product_data.update({
                'product_id': product_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'status': product_data.get('status', 'active'),
                'view_count': 0,
                'sales_count': 0
            })
            
            self.db.collection('products').document(product_id).set(product_data)
            
            logger.info(f"Product added: {product_id}")
            return self._success_response({'product_id': product_id}, "Product added successfully")
            
        except Exception as e:
            return self._handle_error("add_product", e)

    def update_product(self, product_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update product details by product ID
        Security: Product owner or admin only
        """
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            product_ref = self.db.collection('products').document(product_id)
            product_ref.update(update_data)
            
            logger.info(f"Product updated: {product_id}")
            return self._success_response(message="Product updated successfully")
            
        except NotFound:
            return self._handle_error("update_product", Exception("Product not found"))
        except Exception as e:
            return self._handle_error("update_product", e)

    def get_product(self, product_id: str, increment_view: bool = True) -> Dict[str, Any]:
        """
        Fetch product by product ID
        Security: Public read access
        """
        try:
            product_ref = self.db.collection('products').document(product_id)
            product_doc = product_ref.get()
            
            if not product_doc.exists:
                return self._handle_error("get_product", Exception("Product not found"))
            
            product_data = product_doc.to_dict()
            
            # Increment view count if requested
            if increment_view:
                product_ref.update({'view_count': firestore.Increment(1)})
            
            return self._success_response(product_data)
            
        except Exception as e:
            return self._handle_error("get_product", e)

    def get_products_with_filters(self, filters: Dict[str, Any] = None, 
                                limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch products with optional filters: category, subcategory, tags, price range, sellerId
        Security: Public read access
        Uses optimized query strategy with fallback for missing indexes
        """
        try:
            # Start with base query - always filter by status first (has single-field index)
            query = self.db.collection('products')
            status = filters.get('status', 'active') if filters else 'active'
            query = query.where(filter=FieldFilter('status', '==', status))
            
            # Apply additional filters in optimal order for indexing
            if filters:
                # Apply equality filters first (better for composite indexes)
                if 'category_id' in filters:
                    query = query.where(filter=FieldFilter('category_id', '==', filters['category_id']))
                if 'subcategory_id' in filters:
                    query = query.where(filter=FieldFilter('subcategory_id', '==', filters['subcategory_id']))
                if 'seller_id' in filters:
                    query = query.where(filter=FieldFilter('seller_id', '==', filters['seller_id']))
                
                # Apply range filters (Firestore allows multiple range filters on same field)
                if 'min_price' in filters:
                    query = query.where(filter=FieldFilter('price', '>=', filters['min_price']))
                if 'max_price' in filters:
                    query = query.where(filter=FieldFilter('price', '<=', filters['max_price']))
                
                # Apply array filters last (most expensive)
                if 'tags' in filters and filters['tags']:
                    if isinstance(filters['tags'], list):
                        query = query.where(filter=FieldFilter('tags', 'array_contains_any', filters['tags']))
                    else:
                        query = query.where(filter=FieldFilter('tags', 'array_contains', filters['tags']))
            
            # Add ordering and pagination
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            if last_doc_id:
                try:
                    last_doc = self.db.collection('products').document(last_doc_id).get()
                    if last_doc.exists:
                        query = query.start_after(last_doc)
                except Exception as e:
                    logger.warning(f"Failed to use cursor pagination: {e}")
            
            # Execute query with error handling for missing indexes
            try:
                docs = list(query.stream())
                products = []
                last_doc = None
                
                for doc in docs:
                    product_data = doc.to_dict()
                    product_data['id'] = doc.id  # Add document ID
                    products.append(product_data)
                    last_doc = doc
                
                return self._success_response({
                    'products': products,
                    'last_doc_id': last_doc.id if last_doc else None,
                    'has_more': len(products) == limit,
                    'filters_applied': filters or {}
                })
                
            except Exception as query_error:
                if "requires an index" in str(query_error):
                    # Fallback to simpler query
                    logger.warning(f"Complex query failed, using fallback: {query_error}")
                    return self._execute_simple_product_query(filters, limit, last_doc_id)
                else:
                    raise query_error
            
        except Exception as e:
            return self._handle_error("get_products_with_filters", e)
    
    def _execute_simple_product_query(self, filters: Dict[str, Any], limit: int, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fallback query for when complex indexes are missing
        Uses only basic filters and client-side filtering
        """
        try:
            # Use only status filter (guaranteed to have single-field index)
            query = self.db.collection('products')
            status = filters.get('status', 'active') if filters else 'active'
            query = query.where(filter=FieldFilter('status', '==', status))
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
            query = query.limit(limit * 3)  # Get more results for client-side filtering
            
            docs = list(query.stream())
            
            # Apply additional filters client-side
            filtered_products = []
            for doc in docs:
                product_data = doc.to_dict()
                product_data['id'] = doc.id
                
                # Apply client-side filters
                if self._product_matches_filters(product_data, filters):
                    filtered_products.append(product_data)
                    if len(filtered_products) >= limit:
                        break
            
            return self._success_response({
                'products': filtered_products,
                'last_doc_id': filtered_products[-1]['id'] if filtered_products else None,
                'has_more': len(filtered_products) == limit,
                'filters_applied': filters or {},
                'fallback_used': True
            })
            
        except Exception as e:
            raise e
    
    def _product_matches_filters(self, product_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if product matches filters (client-side filtering)
        """
        if not filters:
            return True
        
        # Check category
        if 'category_id' in filters and product_data.get('category_id') != filters['category_id']:
            return False
        
        # Check subcategory
        if 'subcategory_id' in filters and product_data.get('subcategory_id') != filters['subcategory_id']:
            return False
        
        # Check seller
        if 'seller_id' in filters and product_data.get('seller_id') != filters['seller_id']:
            return False
        
        # Check price range
        price = product_data.get('price', 0)
        if 'min_price' in filters and price < filters['min_price']:
            return False
        if 'max_price' in filters and price > filters['max_price']:
            return False
        
        # Check tags
        if 'tags' in filters and filters['tags']:
            product_tags = product_data.get('tags', [])
            filter_tags = filters['tags'] if isinstance(filters['tags'], list) else [filters['tags']]
            if not any(tag in product_tags for tag in filter_tags):
                return False
        
        return True

    def get_active_products(self, limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch all active products (status=='active') with optimized query and performance monitoring
        Security: Public read access
        Uses index: products (status ASC, created_at DESC)
        """
        try:
            # Create optimized query with proper indexing
            filters = [('status', '==', 'active')]
            order_by = [('created_at', firestore.Query.DESCENDING)]
            
            base_query = self._optimize_query_with_index('products', filters, order_by)
            paginated_query, _ = self._paginate_query(base_query, limit, last_doc_id)
            
            # Execute query with performance monitoring
            docs, execution_time = self._execute_query_with_monitoring(paginated_query, 'get_active_products')
            
            # Check if there are more results
            has_more = len(docs) > limit
            if has_more:
                docs = docs[:limit]  # Remove the extra document
            
            # Process results
            products = []
            for doc in docs:
                product_data = doc.to_dict()
                product_data['id'] = doc.id  # Add document ID
                
                # Remove sensitive fields for public access
                product_data.pop('seller_email', None)
                product_data.pop('cost_price', None)
                
                products.append(product_data)
            
            return self._success_response(
                data=products,
                message=f"Retrieved {len(products)} active products in {execution_time:.3f}s"
            )
            
        except Exception as e:
            return self._handle_error("get_active_products", e)

    def archive_product(self, product_id: str, status: str = 'archived') -> Dict[str, Any]:
        """
        Mark a product as 'inactive' or 'archived'
        Security: Product owner or admin only
        """
        try:
            product_ref = self.db.collection('products').document(product_id)
            product_ref.update({
                'status': status,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'archived_at': firestore.SERVER_TIMESTAMP if status == 'archived' else None
            })
            
            logger.info(f"Product archived: {product_id}")
            return self._success_response(message=f"Product marked as {status}")
            
        except NotFound:
            return self._handle_error("archive_product", Exception("Product not found"))
        except Exception as e:
            return self._handle_error("archive_product", e)

    def search_products(self, keywords: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search products by keywords in title/description
        Note: Firestore doesn't support full-text search natively. 
        This is a basic implementation. Consider using Algolia or Elasticsearch for production.
        Security: Public read access
        """
        try:
            # Convert keywords to lowercase for case-insensitive search
            keywords_lower = keywords.lower()
            
            # Get all active products and filter in Python (not ideal for large datasets)
            products_ref = (self.db.collection('products')
                           .where(filter=FieldFilter('status', '==', 'active'))
                           .limit(100))  # Limit initial fetch
            
            docs = products_ref.stream()
            matching_products = []
            
            for doc in docs:
                product_data = doc.to_dict()
                title = product_data.get('title', '').lower()
                description = product_data.get('description', '').lower()
                
                if keywords_lower in title or keywords_lower in description:
                    matching_products.append(product_data)
                    
                if len(matching_products) >= limit:
                    break
            
            return self._success_response({
                'products': matching_products,
                'search_query': keywords,
                'total_found': len(matching_products)
            })
            
        except Exception as e:
            return self._handle_error("search_products", e)

    def batch_update_products(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch update prices or inventory (for admin or seller)
        Security: Admin or product owner only
        """
        try:
            batch = self.db.batch()
            updated_products = []
            
            for update in updates:
                product_id = update.get('product_id')
                if not product_id:
                    continue
                    
                product_ref = self.db.collection('products').document(product_id)
                update_data = update.get('data', {})
                update_data['updated_at'] = firestore.SERVER_TIMESTAMP
                
                batch.update(product_ref, update_data)
                updated_products.append(product_id)
            
            batch.commit()
            
            logger.info(f"Batch updated {len(updated_products)} products")
            return self._success_response({
                'updated_products': updated_products,
                'count': len(updated_products)
            }, "Batch update completed successfully")
            
        except Exception as e:
            return self._handle_error("batch_update_products", e)

    def get_featured_products(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get a list of featured products
        Security: Public read access
        """
        try:
            query = (self.db.collection('products')
                    .where(filter=FieldFilter('status', '==', 'active'))
                    .where(filter=FieldFilter('is_featured', '==', True))
                    .limit(limit)
                    .order_by('created_at', direction=firestore.Query.DESCENDING))
            
            docs = query.stream()
            products = [doc.to_dict() for doc in docs]
            
            return self._success_response({'featured_products': products})
            
        except Exception as e:
            return self._handle_error("get_featured_products", e)

    # ==================== ORDERS OPERATIONS ====================
    
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new order and all necessary subdocuments (order items, timeline events)
        Security: Authenticated users only
        """
        try:
            order_id = str(uuid.uuid4())
            
            # Prepare order data
            order_data.update({
                'order_id': order_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'status': 'pending',
                'order_number': f"ORD-{datetime.now().strftime('%Y%m%d')}-{order_id[:8].upper()}"
            })
            
            # Use transaction to ensure data consistency
            transaction = self.db.transaction()
            
            @firestore.transactional
            def create_order_transaction(transaction):
                # Create main order document
                order_ref = self.db.collection('orders').document(order_id)
                transaction.set(order_ref, order_data)
                
                # Create initial timeline event
                timeline_ref = order_ref.collection('timeline').document()
                transaction.set(timeline_ref, {
                    'event': 'order_created',
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'details': 'Order created successfully',
                    'user_id': order_data.get('customer_id')
                })
                
                # Create order items subcollection
                if 'items' in order_data:
                    for item in order_data['items']:
                        item_ref = order_ref.collection('items').document()
                        transaction.set(item_ref, {
                            **item,
                            'created_at': firestore.SERVER_TIMESTAMP
                        })
            
            create_order_transaction(transaction)
            
            logger.info(f"Order created: {order_id}")
            return self._success_response({'order_id': order_id}, "Order created successfully")
            
        except Exception as e:
            return self._handle_error("create_order", e)

    def get_order(self, order_id: str, include_items: bool = True, include_timeline: bool = False) -> Dict[str, Any]:
        """
        Fetch order by order ID with optional subcollections
        Security: Customer can access own orders, seller can access their orders, admin can access all
        """
        try:
            order_ref = self.db.collection('orders').document(order_id)
            order_doc = order_ref.get()
            
            if not order_doc.exists:
                return self._handle_error("get_order", Exception("Order not found"))
            
            order_data = order_doc.to_dict()
            
            # Include order items if requested
            if include_items:
                items_ref = order_ref.collection('items')
                items_docs = items_ref.stream()
                order_data['items'] = [item.to_dict() for item in items_docs]
            
            # Include timeline if requested
            if include_timeline:
                timeline_ref = order_ref.collection('timeline').order_by('timestamp')
                timeline_docs = timeline_ref.stream()
                order_data['timeline'] = [event.to_dict() for event in timeline_docs]
            
            return self._success_response(order_data)
            
        except Exception as e:
            return self._handle_error("get_order", e)

    def get_user_orders(self, user_id: str, limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch all orders by user/customer ID (order history)
        Security: Users can only access their own orders
        """
        try:
            query = (self.db.collection('orders')
                    .where(filter=FieldFilter('customer_id', '==', user_id))
                    .limit(limit)
                    .order_by('created_at', direction=firestore.Query.DESCENDING))
            
            if last_doc_id:
                last_doc = self.db.collection('orders').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            orders = []
            last_doc = None
            
            for doc in docs:
                order_data = doc.to_dict()
                orders.append(order_data)
                last_doc = doc
            
            return self._success_response({
                'orders': orders,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(orders) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_user_orders", e)

    def get_seller_orders(self, seller_id: str, limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch all orders for a seller
        Security: Sellers can only access their own orders
        """
        try:
            query = (self.db.collection('orders')
                    .where(filter=FieldFilter('seller_id', '==', seller_id))
                    .limit(limit)
                    .order_by('created_at', direction=firestore.Query.DESCENDING))
            
            if last_doc_id:
                last_doc = self.db.collection('orders').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            orders = []
            last_doc = None
            
            for doc in docs:
                order_data = doc.to_dict()
                orders.append(order_data)
                last_doc = doc
            
            return self._success_response({
                'orders': orders,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(orders) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_seller_orders", e)

    def update_order_status(self, order_id: str, new_status: str, 
                           fulfillment_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update order status, add fulfillment details (tracking, carrier info)
        Security: Seller or admin only
        """
        try:
            order_ref = self.db.collection('orders').document(order_id)
            
            update_data = {
                'status': new_status,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if fulfillment_details:
                update_data.update(fulfillment_details)
            
            # Use transaction to update order and add timeline event
            transaction = self.db.transaction()
            
            @firestore.transactional
            def update_order_transaction(transaction):
                transaction.update(order_ref, update_data)
                
                # Add timeline event
                timeline_ref = order_ref.collection('timeline').document()
                transaction.set(timeline_ref, {
                    'event': f'status_changed_to_{new_status}',
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'details': f'Order status changed to {new_status}',
                    'fulfillment_details': fulfillment_details
                })
            
            update_order_transaction(transaction)
            
            logger.info(f"Order status updated: {order_id} -> {new_status}")
            return self._success_response(message="Order status updated successfully")
            
        except NotFound:
            return self._handle_error("update_order_status", Exception("Order not found"))
        except Exception as e:
            return self._handle_error("update_order_status", e)

    def cancel_order(self, order_id: str, reason: str, refund_amount: float = None) -> Dict[str, Any]:
        """
        Cancel or refund an order
        Security: Customer can cancel pending orders, admin can cancel any order
        """
        try:
            order_ref = self.db.collection('orders').document(order_id)
            
            update_data = {
                'status': 'cancelled',
                'cancelled_at': firestore.SERVER_TIMESTAMP,
                'cancellation_reason': reason,
                'updated_at': firestore.SERVER_TIMESTAMP
            }
            
            if refund_amount is not None:
                update_data['refund_amount'] = refund_amount
                update_data['refund_status'] = 'pending'
            
            # Use transaction
            transaction = self.db.transaction()
            
            @firestore.transactional
            def cancel_order_transaction(transaction):
                transaction.update(order_ref, update_data)
                
                # Add timeline event
                timeline_ref = order_ref.collection('timeline').document()
                transaction.set(timeline_ref, {
                    'event': 'order_cancelled',
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'details': f'Order cancelled: {reason}',
                    'refund_amount': refund_amount
                })
            
            cancel_order_transaction(transaction)
            
            logger.info(f"Order cancelled: {order_id}")
            return self._success_response(message="Order cancelled successfully")
            
        except NotFound:
            return self._handle_error("cancel_order", Exception("Order not found"))
        except Exception as e:
            return self._handle_error("cancel_order", e)

    def add_order_timeline_event(self, order_id: str, event: str, details: str, 
                                user_id: str = None) -> Dict[str, Any]:
        """
        Add a timeline event to an order
        Security: Seller or admin only
        """
        try:
            order_ref = self.db.collection('orders').document(order_id)
            timeline_ref = order_ref.collection('timeline').document()
            
            timeline_data = {
                'event': event,
                'details': details,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'user_id': user_id
            }
            
            timeline_ref.set(timeline_data)
            
            logger.info(f"Timeline event added to order {order_id}: {event}")
            return self._success_response(message="Timeline event added successfully")
            
        except Exception as e:
            return self._handle_error("add_order_timeline_event", e)

    # ==================== CATEGORIES OPERATIONS ====================
    
    def list_categories(self, parent_id: str = None) -> Dict[str, Any]:
        """
        List all categories or subcategories
        Security: Public read access
        """
        try:
            query = self.db.collection('categories')
            
            if parent_id:
                query = query.where(filter=FieldFilter('parent_id', '==', parent_id))
            else:
                query = query.where(filter=FieldFilter('parent_id', '==', None))
            
            query = query.order_by('sort_order').order_by('name')
            docs = query.stream()
            categories = [doc.to_dict() for doc in docs]
            
            return self._success_response({'categories': categories})
            
        except Exception as e:
            return self._handle_error("list_categories", e)

    def add_category(self, category_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new category
        Security: Admin only
        """
        try:
            category_id = str(uuid.uuid4())
            
            category_data.update({
                'category_id': category_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            })
            
            self.db.collection('categories').document(category_id).set(category_data)
            
            logger.info(f"Category added: {category_id}")
            return self._success_response({'category_id': category_id}, "Category added successfully")
            
        except Exception as e:
            return self._handle_error("add_category", e)

    def update_category(self, category_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a category (name, image, parentId, etc)
        Security: Admin only
        """
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            category_ref = self.db.collection('categories').document(category_id)
            category_ref.update(update_data)
            
            logger.info(f"Category updated: {category_id}")
            return self._success_response(message="Category updated successfully")
            
        except NotFound:
            return self._handle_error("update_category", Exception("Category not found"))
        except Exception as e:
            return self._handle_error("update_category", e)

    def archive_category(self, category_id: str) -> Dict[str, Any]:
        """
        Archive a category (soft delete)
        Security: Admin only
        """
        try:
            category_ref = self.db.collection('categories').document(category_id)
            category_ref.update({
                'is_active': False,
                'archived_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Category archived: {category_id}")
            return self._success_response(message="Category archived successfully")
            
        except NotFound:
            return self._handle_error("archive_category", Exception("Category not found"))
        except Exception as e:
            return self._handle_error("archive_category", e)

    # ==================== INVENTORY OPERATIONS ====================
    
    def add_inventory_record(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add new inventory record for a product at a warehouse
        Security: Seller or admin only
        """
        try:
            inventory_id = str(uuid.uuid4())
            
            inventory_data.update({
                'inventory_id': inventory_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'last_movement_date': firestore.SERVER_TIMESTAMP
            })
            
            self.db.collection('inventory').document(inventory_id).set(inventory_data)
            
            logger.info(f"Inventory record added: {inventory_id}")
            return self._success_response({'inventory_id': inventory_id}, "Inventory record added successfully")
            
        except Exception as e:
            return self._handle_error("add_inventory_record", e)

    def update_inventory_quantities(self, product_id: str, warehouse_id: str, 
                                   quantity_change: int, movement_type: str, 
                                   notes: str = None) -> Dict[str, Any]:
        """
        Update inventory quantities (stock in, stock out, adjustment)
        Security: Seller or admin only
        """
        try:
            # Find existing inventory record
            inventory_query = (self.db.collection('inventory')
                             .where(filter=FieldFilter('product_id', '==', product_id))
                             .where(filter=FieldFilter('warehouse_id', '==', warehouse_id))
                             .limit(1))
            
            docs = list(inventory_query.stream())
            
            if not docs:
                return self._handle_error("update_inventory_quantities", 
                                        Exception("Inventory record not found"))
            
            inventory_doc = docs[0]
            inventory_ref = self.db.collection('inventory').document(inventory_doc.id)
            
            # Use transaction for atomic update
            transaction = self.db.transaction()
            
            @firestore.transactional
            def update_inventory_transaction(transaction):
                # Get current inventory data
                current_data = transaction.get(inventory_ref).to_dict()
                current_stock = current_data.get('available_stock', 0)
                
                # Calculate new stock level
                new_stock = max(0, current_stock + quantity_change)
                
                # Update inventory record
                transaction.update(inventory_ref, {
                    'available_stock': new_stock,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'last_movement_date': firestore.SERVER_TIMESTAMP
                })
                
                # Create movement log entry
                movement_ref = inventory_ref.collection('movements').document()
                transaction.set(movement_ref, {
                    'movement_type': movement_type,
                    'quantity_change': quantity_change,
                    'stock_before': current_stock,
                    'stock_after': new_stock,
                    'timestamp': firestore.SERVER_TIMESTAMP,
                    'notes': notes
                })
            
            update_inventory_transaction(transaction)
            
            logger.info(f"Inventory updated for product {product_id} at warehouse {warehouse_id}")
            return self._success_response(message="Inventory quantities updated successfully")
            
        except Exception as e:
            return self._handle_error("update_inventory_quantities", e)

    def get_product_inventory(self, product_id: str) -> Dict[str, Any]:
        """
        Fetch inventory for a given product (all warehouses)
        Security: Seller can view own products, admin can view all
        """
        try:
            inventory_query = (self.db.collection('inventory')
                             .where(filter=FieldFilter('product_id', '==', product_id)))
            
            docs = inventory_query.stream()
            inventory_records = []
            total_stock = 0
            
            for doc in docs:
                inventory_data = doc.to_dict()
                inventory_records.append(inventory_data)
                total_stock += inventory_data.get('available_stock', 0)
            
            return self._success_response({
                'product_id': product_id,
                'inventory_records': inventory_records,
                'total_stock': total_stock,
                'warehouse_count': len(inventory_records)
            })
            
        except Exception as e:
            return self._handle_error("get_product_inventory", e)

    def get_low_stock_items(self, limit: int = 50) -> Dict[str, Any]:
        """
        Fetch low-stock items (where availableStock <= lowStockThreshold)
        Security: Seller can view own products, admin can view all
        """
        try:
            # Note: Firestore doesn't support complex queries with computed fields
            # This implementation fetches all inventory and filters in Python
            # For production, consider maintaining a separate low_stock collection
            
            inventory_query = self.db.collection('inventory').limit(1000)
            docs = inventory_query.stream()
            
            low_stock_items = []
            
            for doc in docs:
                inventory_data = doc.to_dict()
                available_stock = inventory_data.get('available_stock', 0)
                low_stock_threshold = inventory_data.get('low_stock_threshold', 10)
                
                if available_stock <= low_stock_threshold:
                    low_stock_items.append(inventory_data)
                    
                if len(low_stock_items) >= limit:
                    break
            
            return self._success_response({
                'low_stock_items': low_stock_items,
                'count': len(low_stock_items)
            })
            
        except Exception as e:
            return self._handle_error("get_low_stock_items", e)

    def get_warehouse_inventory(self, warehouse_id: str, limit: int = 50, 
                               last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch inventory by warehouse
        Security: Warehouse staff or admin only
        """
        try:
            query = (self.db.collection('inventory')
                    .where(filter=FieldFilter('warehouse_id', '==', warehouse_id))
                    .limit(limit)
                    .order_by('updated_at', direction=firestore.Query.DESCENDING))
            
            if last_doc_id:
                last_doc = self.db.collection('inventory').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            inventory_records = []
            last_doc = None
            
            for doc in docs:
                inventory_data = doc.to_dict()
                inventory_records.append(inventory_data)
                last_doc = doc
            
            return self._success_response({
                'warehouse_id': warehouse_id,
                'inventory_records': inventory_records,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(inventory_records) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_warehouse_inventory", e)

    # ==================== WAREHOUSES OPERATIONS ====================
    
    def create_warehouse(self, warehouse_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new warehouse
        Security: Admin only
        """
        try:
            warehouse_id = str(uuid.uuid4())
            
            warehouse_data.update({
                'warehouse_id': warehouse_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            })
            
            self.db.collection('warehouses').document(warehouse_id).set(warehouse_data)
            
            logger.info(f"Warehouse created: {warehouse_id}")
            return self._success_response({'warehouse_id': warehouse_id}, "Warehouse created successfully")
            
        except Exception as e:
            return self._handle_error("create_warehouse", e)

    def list_warehouses(self, active_only: bool = True) -> Dict[str, Any]:
        """
        List all warehouses
        Security: Admin or warehouse staff
        """
        try:
            query = self.db.collection('warehouses')
            
            if active_only:
                query = query.where(filter=FieldFilter('is_active', '==', True))
            
            query = query.order_by('name')
            docs = query.stream()
            warehouses = [doc.to_dict() for doc in docs]
            
            return self._success_response({'warehouses': warehouses})
            
        except Exception as e:
            return self._handle_error("list_warehouses", e)

    def get_warehouse_details(self, warehouse_id: str) -> Dict[str, Any]:
        """
        Get warehouse details
        Security: Admin or warehouse staff
        """
        try:
            warehouse_ref = self.db.collection('warehouses').document(warehouse_id)
            warehouse_doc = warehouse_ref.get()
            
            if not warehouse_doc.exists:
                return self._handle_error("get_warehouse_details", Exception("Warehouse not found"))
            
            warehouse_data = warehouse_doc.to_dict()
            
            return self._success_response(warehouse_data)
            
        except Exception as e:
            return self._handle_error("get_warehouse_details", e)

    def update_warehouse_details(self, warehouse_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update warehouse details
        Security: Admin only
        """
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            warehouse_ref = self.db.collection('warehouses').document(warehouse_id)
            warehouse_ref.update(update_data)
            
            logger.info(f"Warehouse updated: {warehouse_id}")
            return self._success_response(message="Warehouse details updated successfully")
            
        except NotFound:
            return self._handle_error("update_warehouse_details", Exception("Warehouse not found"))
        except Exception as e:
            return self._handle_error("update_warehouse_details", e)

    # ==================== CARTS OPERATIONS ====================
    
    def initialize_cart(self, user_id: str) -> Dict[str, Any]:
        """
        Create/initialize a cart for a user
        Security: Authenticated users only
        """
        try:
            cart_data = {
                'user_id': user_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'items': [],
                'total_items': 0,
                'total_amount': 0.0,
                'currency': 'USD'
            }
            
            # Use user_id as cart document ID for easy retrieval
            cart_ref = self.db.collection('carts').document(user_id)
            cart_ref.set(cart_data)
            
            logger.info(f"Cart initialized for user: {user_id}")
            return self._success_response({'cart_id': user_id}, "Cart initialized successfully")
            
        except Exception as e:
            return self._handle_error("initialize_cart", e)

    def add_item_to_cart(self, user_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add an item to cart
        Security: Users can only modify their own cart
        """
        try:
            cart_ref = self.db.collection('carts').document(user_id)
            
            # Use transaction for atomic updates
            @firestore.transactional
            def add_item_transaction(transaction):
                # Get cart document within transaction
                cart_doc = transaction.get(cart_ref)
                
                # Check if cart exists
                cart_exists = cart_doc.exists if hasattr(cart_doc, 'exists') else False
                
                if not cart_exists:
                    # Initialize cart if it doesn't exist
                    cart_data = {
                        'user_id': user_id,
                        'created_at': firestore.SERVER_TIMESTAMP,
                        'updated_at': firestore.SERVER_TIMESTAMP,
                        'items': [],
                        'total_items': 0,
                        'total_amount': 0.0
                    }
                    transaction.set(cart_ref, cart_data)
                    current_items = []
                else:
                    cart_data = cart_doc.to_dict() if hasattr(cart_doc, 'to_dict') else {}
                    current_items = cart_data.get('items', [])
                
                # Check if item already exists in cart
                item_exists = False
                for i, existing_item in enumerate(current_items):
                    if (existing_item.get('product_id') == item_data.get('product_id') and
                        existing_item.get('variant_id') == item_data.get('variant_id')):
                        # Update quantity
                        current_items[i]['quantity'] += item_data.get('quantity', 1)
                        item_exists = True
                        break
                
                if not item_exists:
                    # Add new item
                    new_item = item_data.copy()
                    # Don't add SERVER_TIMESTAMP to item data in transaction
                    current_items.append(new_item)
                
                # Recalculate totals
                total_items = sum(item.get('quantity', 0) for item in current_items)
                total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in current_items)
                
                # Update or set cart data
                update_data = {
                    'items': current_items,
                    'total_items': total_items,
                    'total_amount': total_amount,
                    'updated_at': firestore.SERVER_TIMESTAMP
                }
                
                if cart_exists:
                    transaction.update(cart_ref, update_data)
                else:
                    # If cart was just created, merge the update data
                    update_data['user_id'] = user_id
                    update_data['created_at'] = firestore.SERVER_TIMESTAMP
                    transaction.set(cart_ref, update_data)
            
            # Execute transaction
            transaction = self.db.transaction()
            add_item_transaction(transaction)
            
            logger.info(f"Item added to cart for user: {user_id}")
            return self._success_response(message="Item added to cart successfully")
            
        except Exception as e:
            return self._handle_error("add_item_to_cart", e)

    def remove_item_from_cart(self, user_id: str, product_id: str, variant_id: str = None) -> Dict[str, Any]:
        """
        Remove an item from cart
        Security: Users can only modify their own cart
        """
        try:
            cart_ref = self.db.collection('carts').document(user_id)
            
            @firestore.transactional
            def remove_item_transaction(transaction):
                cart_doc = transaction.get(cart_ref)
                
                # Check if cart exists
                cart_exists = cart_doc.exists if hasattr(cart_doc, 'exists') else False
                
                if not cart_exists:
                    raise Exception("Cart not found")
                
                cart_data = cart_doc.to_dict() if hasattr(cart_doc, 'to_dict') else {}
                current_items = cart_data.get('items', [])
                
                # Remove item
                updated_items = [
                    item for item in current_items 
                    if not (item.get('product_id') == product_id and 
                           item.get('variant_id') == variant_id)
                ]
                
                # Recalculate totals
                total_items = sum(item.get('quantity', 0) for item in updated_items)
                total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in updated_items)
                
                # Update cart
                transaction.update(cart_ref, {
                    'items': updated_items,
                    'total_items': total_items,
                    'total_amount': total_amount,
                    'updated_at': firestore.SERVER_TIMESTAMP
                })
            
            # Execute transaction
            transaction = self.db.transaction()
            remove_item_transaction(transaction)
            
            logger.info(f"Item removed from cart for user: {user_id}")
            return self._success_response(message="Item removed from cart successfully")
            
        except Exception as e:
            return self._handle_error("remove_item_from_cart", e)

    def update_cart_item(self, user_id: str, product_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update quantity or variant of a cart item
        Security: Users can only modify their own cart
        Note: Uses non-transactional update for simplicity since cart operations are less critical
        """
        try:
            cart_ref = self.db.collection('carts').document(user_id)
            
            # Get current cart data
            cart_doc = cart_ref.get()
            if not cart_doc.exists:
                return self._handle_error("update_cart_item", Exception("Cart not found"))
            
            cart_data = cart_doc.to_dict()
            current_items = cart_data.get('items', [])
            
            # Find and update item
            item_found = False
            for item in current_items:
                if item.get('product_id') == product_id:
                    item.update(update_data)
                    item_found = True
                    break
            
            if not item_found:
                return self._handle_error("update_cart_item", Exception("Item not found in cart"))
            
            # Recalculate totals
            total_items = sum(item.get('quantity', 0) for item in current_items)
            total_amount = sum(item.get('price', 0) * item.get('quantity', 0) for item in current_items)
            
            # Update cart with new data
            cart_ref.update({
                'items': current_items,
                'total_items': total_items,
                'total_amount': total_amount,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Cart item updated for user: {user_id}")
            return self._success_response(message="Cart item updated successfully")
            
        except Exception as e:
            return self._handle_error("update_cart_item", e)

    def get_user_cart(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch cart for a user
        Security: Users can only access their own cart
        """
        try:
            cart_ref = self.db.collection('carts').document(user_id)
            cart_doc = cart_ref.get()
            
            if not cart_doc.exists:
                # Return empty cart structure
                return self._success_response({
                    'user_id': user_id,
                    'items': [],
                    'total_items': 0,
                    'total_amount': 0.0,
                    'currency': 'USD'
                })
            
            cart_data = cart_doc.to_dict()
            return self._success_response(cart_data)
            
        except Exception as e:
            return self._handle_error("get_user_cart", e)

    def clear_cart(self, user_id: str) -> Dict[str, Any]:
        """
        Empty/clear cart after order is placed
        Security: Users can only clear their own cart
        """
        try:
            cart_ref = self.db.collection('carts').document(user_id)
            cart_ref.update({
                'items': [],
                'total_items': 0,
                'total_amount': 0.0,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'cleared_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Cart cleared for user: {user_id}")
            return self._success_response(message="Cart cleared successfully")
            
        except Exception as e:
            return self._handle_error("clear_cart", e)

    # ==================== REVIEWS OPERATIONS ====================
    
    def submit_review(self, review_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a review for a product
        Security: Authenticated users only, must have purchased the product
        """
        try:
            review_id = str(uuid.uuid4())
            
            review_data.update({
                'review_id': review_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'status': 'pending',  # pending, approved, rejected
                'helpful_count': 0,
                'reported_count': 0
            })
            
            self.db.collection('reviews').document(review_id).set(review_data)
            
            logger.info(f"Review submitted: {review_id}")
            return self._success_response({'review_id': review_id}, "Review submitted successfully")
            
        except Exception as e:
            return self._handle_error("submit_review", e)

    def get_product_reviews(self, product_id: str, status: str = 'approved', 
                           limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch reviews for a product (paginated)
        Security: Public read access for approved reviews
        """
        try:
            query = (self.db.collection('reviews')
                    .where(filter=FieldFilter('product_id', '==', product_id))
                    .where(filter=FieldFilter('status', '==', status))
                    .limit(limit)
                    .order_by('created_at', direction=firestore.Query.DESCENDING))
            
            if last_doc_id:
                last_doc = self.db.collection('reviews').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            reviews = []
            last_doc = None
            
            for doc in docs:
                review_data = doc.to_dict()
                reviews.append(review_data)
                last_doc = doc
            
            return self._success_response({
                'product_id': product_id,
                'reviews': reviews,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(reviews) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_product_reviews", e)

    def get_user_reviews(self, user_id: str, limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch reviews by user
        Security: Users can only access their own reviews
        """
        try:
            query = (self.db.collection('reviews')
                    .where(filter=FieldFilter('user_id', '==', user_id))
                    .limit(limit)
                    .order_by('created_at', direction=firestore.Query.DESCENDING))
            
            if last_doc_id:
                last_doc = self.db.collection('reviews').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            reviews = []
            last_doc = None
            
            for doc in docs:
                review_data = doc.to_dict()
                reviews.append(review_data)
                last_doc = doc
            
            return self._success_response({
                'user_id': user_id,
                'reviews': reviews,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(reviews) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_user_reviews", e)

    def update_review(self, review_id: str, update_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Update review (if allowed)
        Security: Users can only update their own reviews within time limit
        """
        try:
            review_ref = self.db.collection('reviews').document(review_id)
            review_doc = review_ref.get()
            
            if not review_doc.exists:
                return self._handle_error("update_review", Exception("Review not found"))
            
            review_data = review_doc.to_dict()
            
            # Check if user owns the review
            if review_data.get('user_id') != user_id:
                return self._handle_error("update_review", Exception("Unauthorized"))
            
            # Add update timestamp
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            update_data['is_edited'] = True
            
            review_ref.update(update_data)
            
            logger.info(f"Review updated: {review_id}")
            return self._success_response(message="Review updated successfully")
            
        except Exception as e:
            return self._handle_error("update_review", e)

    def moderate_review(self, review_id: str, action: str, moderator_id: str, notes: str = None) -> Dict[str, Any]:
        """
        Moderate (approve/reject) a review
        Security: Admin or moderator only
        """
        try:
            if action not in ['approved', 'rejected']:
                return self._handle_error("moderate_review", Exception("Invalid action"))
            
            review_ref = self.db.collection('reviews').document(review_id)
            review_ref.update({
                'status': action,
                'moderated_at': firestore.SERVER_TIMESTAMP,
                'moderator_id': moderator_id,
                'moderation_notes': notes,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Review moderated: {review_id} -> {action}")
            return self._success_response(message=f"Review {action} successfully")
            
        except NotFound:
            return self._handle_error("moderate_review", Exception("Review not found"))
        except Exception as e:
            return self._handle_error("moderate_review", e)

    # ==================== NOTIFICATIONS OPERATIONS ====================
    
    def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create/send a notification to a user
        Security: System or admin only
        """
        try:
            notification_id = str(uuid.uuid4())
            
            notification_data.update({
                'notification_id': notification_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'is_read': False,
                'read_at': None
            })
            
            self.db.collection('notifications').document(notification_id).set(notification_data)
            
            logger.info(f"Notification created: {notification_id}")
            return self._success_response({'notification_id': notification_id}, "Notification created successfully")
            
        except Exception as e:
            return self._handle_error("create_notification", e)

    def get_user_notifications(self, user_id: str, unread_only: bool = False, 
                              limit: int = 20, last_doc_id: str = None) -> Dict[str, Any]:
        """
        Fetch unread or recent notifications for a user
        Security: Users can only access their own notifications
        """
        try:
            query = (self.db.collection('notifications')
                    .where(filter=FieldFilter('user_id', '==', user_id)))
            
            if unread_only:
                query = query.where(filter=FieldFilter('is_read', '==', False))
            
            query = query.limit(limit).order_by('created_at', direction=firestore.Query.DESCENDING)
            
            if last_doc_id:
                last_doc = self.db.collection('notifications').document(last_doc_id).get()
                if last_doc.exists:
                    query = query.start_after(last_doc)
            
            docs = query.stream()
            notifications = []
            last_doc = None
            
            for doc in docs:
                notification_data = doc.to_dict()
                notifications.append(notification_data)
                last_doc = doc
            
            return self._success_response({
                'notifications': notifications,
                'last_doc_id': last_doc.id if last_doc else None,
                'has_more': len(notifications) == limit
            })
            
        except Exception as e:
            return self._handle_error("get_user_notifications", e)

    def mark_notification_read(self, notification_id: str, user_id: str) -> Dict[str, Any]:
        """
        Mark notification as read
        Security: Users can only mark their own notifications as read
        """
        try:
            notification_ref = self.db.collection('notifications').document(notification_id)
            notification_doc = notification_ref.get()
            
            if not notification_doc.exists:
                return self._handle_error("mark_notification_read", Exception("Notification not found"))
            
            notification_data = notification_doc.to_dict()
            
            # Check if user owns the notification
            if notification_data.get('user_id') != user_id:
                return self._handle_error("mark_notification_read", Exception("Unauthorized"))
            
            notification_ref.update({
                'is_read': True,
                'read_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Notification marked as read: {notification_id}")
            return self._success_response(message="Notification marked as read")
            
        except Exception as e:
            return self._handle_error("mark_notification_read", e)

    # ==================== SUPPLIERS OPERATIONS ====================
    
    def add_supplier(self, supplier_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new supplier
        Security: Admin only
        """
        try:
            supplier_id = str(uuid.uuid4())
            
            supplier_data.update({
                'supplier_id': supplier_id,
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'is_active': True
            })
            
            self.db.collection('suppliers').document(supplier_id).set(supplier_data)
            
            logger.info(f"Supplier added: {supplier_id}")
            return self._success_response({'supplier_id': supplier_id}, "Supplier added successfully")
            
        except Exception as e:
            return self._handle_error("add_supplier", e)

    def update_supplier_info(self, supplier_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update supplier info
        Security: Admin only
        """
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            
            supplier_ref = self.db.collection('suppliers').document(supplier_id)
            supplier_ref.update(update_data)
            
            logger.info(f"Supplier updated: {supplier_id}")
            return self._success_response(message="Supplier info updated successfully")
            
        except NotFound:
            return self._handle_error("update_supplier_info", Exception("Supplier not found"))
        except Exception as e:
            return self._handle_error("update_supplier_info", e)

    def list_suppliers(self, active_only: bool = True) -> Dict[str, Any]:
        """
        List all suppliers
        Security: Admin or authorized personnel only
        """
        try:
            query = self.db.collection('suppliers')
            
            if active_only:
                query = query.where(filter=FieldFilter('is_active', '==', True))
            
            query = query.order_by('name')
            docs = query.stream()
            suppliers = [doc.to_dict() for doc in docs]
            
            return self._success_response({'suppliers': suppliers})
            
        except Exception as e:
            return self._handle_error("list_suppliers", e)

    def get_supplier_by_id(self, supplier_id: str) -> Dict[str, Any]:
        """
        Get supplier by ID
        Security: Admin or authorized personnel only
        """
        try:
            supplier_ref = self.db.collection('suppliers').document(supplier_id)
            supplier_doc = supplier_ref.get()
            
            if not supplier_doc.exists:
                return self._handle_error("get_supplier_by_id", Exception("Supplier not found"))
            
            supplier_data = supplier_doc.to_dict()
            return self._success_response(supplier_data)
            
        except Exception as e:
            return self._handle_error("get_supplier_by_id", e)

    # ==================== COMPOSITE QUERIES / DASHBOARD FUNCTIONS ====================
    
    def get_dashboard_stats(self, seller_id: str = None) -> Dict[str, Any]:
        """
        Get count of orders, active products, users (for admin dashboard)
        Or seller-specific stats if seller_id provided
        Security: Admin can see all stats, sellers can see only their stats
        """
        try:
            stats = {}
            
            if seller_id:
                # Seller-specific stats
                # Count seller's active products
                products_query = (self.db.collection('products')
                                .where(filter=FieldFilter('seller_id', '==', seller_id))
                                .where(filter=FieldFilter('status', '==', 'active')))
                products_count = len(list(products_query.stream()))
                
                # Count seller's orders
                orders_query = (self.db.collection('orders')
                              .where(filter=FieldFilter('seller_id', '==', seller_id)))
                orders_count = len(list(orders_query.stream()))
                
                stats = {
                    'seller_id': seller_id,
                    'active_products': products_count,
                    'total_orders': orders_count
                }
            else:
                # Admin dashboard stats
                # Count all users
                users_query = self.db.collection('users').where(filter=FieldFilter('is_active', '==', True))
                users_count = len(list(users_query.stream()))
                
                # Count active products
                products_query = self.db.collection('products').where(filter=FieldFilter('status', '==', 'active'))
                products_count = len(list(products_query.stream()))
                
                # Count all orders
                orders_query = self.db.collection('orders')
                orders_count = len(list(orders_query.stream()))
                
                # Count pending reviews
                reviews_query = self.db.collection('reviews').where(filter=FieldFilter('status', '==', 'pending'))
                pending_reviews = len(list(reviews_query.stream()))
                
                stats = {
                    'total_users': users_count,
                    'active_products': products_count,
                    'total_orders': orders_count,
                    'pending_reviews': pending_reviews
                }
            
            return self._success_response(stats)
            
        except Exception as e:
            return self._handle_error("get_dashboard_stats", e)

    def get_sales_stats(self, seller_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Get sales stats for a seller: total sales, orders, revenue over a period
        Security: Sellers can only see their own stats, admin can see any seller's stats
        """
        try:
            # Query orders within date range for the seller
            orders_query = (self.db.collection('orders')
                           .where(filter=FieldFilter('seller_id', '==', seller_id))
                           .where(filter=FieldFilter('created_at', '>=', start_date))
                           .where(filter=FieldFilter('created_at', '<=', end_date))
                           .where(filter=FieldFilter('status', 'in', ['completed', 'delivered'])))
            
            orders = list(orders_query.stream())
            
            total_orders = len(orders)
            total_revenue = 0.0
            total_items_sold = 0
            
            for order_doc in orders:
                order_data = order_doc.to_dict()
                total_revenue += order_data.get('total_amount', 0.0)
                
                # Get order items to count total items sold
                items_ref = order_doc.reference.collection('items')
                items = list(items_ref.stream())
                for item_doc in items:
                    item_data = item_doc.to_dict()
                    total_items_sold += item_data.get('quantity', 0)
            
            # Calculate average order value
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0.0
            
            stats = {
                'seller_id': seller_id,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_orders': total_orders,
                'total_revenue': round(total_revenue, 2),
                'total_items_sold': total_items_sold,
                'average_order_value': round(avg_order_value, 2)
            }
            
            return self._success_response(stats)
            
        except Exception as e:
            return self._handle_error("get_sales_stats", e)

    def get_popular_products(self, limit: int = 10, metric: str = 'sales') -> Dict[str, Any]:
        """
        Get most popular products (by orders or cart adds)
        Security: Public read access
        """
        try:
            if metric == 'sales':
                # Sort by sales_count
                query = (self.db.collection('products')
                        .where(filter=FieldFilter('status', '==', 'active'))
                        .order_by('sales_count', direction=firestore.Query.DESCENDING)
                        .limit(limit))
            elif metric == 'views':
                # Sort by view_count
                query = (self.db.collection('products')
                        .where(filter=FieldFilter('status', '==', 'active'))
                        .order_by('view_count', direction=firestore.Query.DESCENDING)
                        .limit(limit))
            else:
                return self._handle_error("get_popular_products", Exception("Invalid metric"))
            
            docs = query.stream()
            products = [doc.to_dict() for doc in docs]
            
            return self._success_response({
                'popular_products': products,
                'metric': metric,
                'limit': limit
            })
            
        except Exception as e:
            return self._handle_error("get_popular_products", e)

    def get_low_stock_alerts(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get real-time low stock alerts
        Security: Admin or warehouse staff only
        """
        try:
            # This is a simplified version - in production, you might maintain
            # a separate collection for low stock alerts or use Cloud Functions
            inventory_query = self.db.collection('inventory').limit(500)
            docs = inventory_query.stream()
            
            low_stock_alerts = []
            
            for doc in docs:
                inventory_data = doc.to_dict()
                available_stock = inventory_data.get('available_stock', 0)
                low_stock_threshold = inventory_data.get('low_stock_threshold', 10)
                
                if available_stock <= low_stock_threshold:
                    # Get product details
                    product_id = inventory_data.get('product_id')
                    if product_id:
                        product_doc = self.db.collection('products').document(product_id).get()
                        if product_doc.exists:
                            product_data = product_doc.to_dict()
                            
                            alert = {
                                'product_id': product_id,
                                'product_name': product_data.get('title', 'Unknown'),
                                'warehouse_id': inventory_data.get('warehouse_id'),
                                'current_stock': available_stock,
                                'threshold': low_stock_threshold,
                                'severity': 'critical' if available_stock == 0 else 'warning'
                            }
                            low_stock_alerts.append(alert)
                
                if len(low_stock_alerts) >= limit:
                    break
            
            return self._success_response({
                'low_stock_alerts': low_stock_alerts,
                'total_alerts': len(low_stock_alerts),
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return self._handle_error("get_low_stock_alerts", e)

    # ==================== UTILITY FUNCTIONS ====================
    
    def batch_operation(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform multiple operations in a single batch
        Security: Varies by operation type
        """
        try:
            batch = self.db.batch()
            results = []
            
            for operation in operations:
                op_type = operation.get('type')
                collection = operation.get('collection')
                doc_id = operation.get('doc_id')
                data = operation.get('data', {})
                
                if not all([op_type, collection, doc_id]):
                    results.append({'error': 'Missing required fields'})
                    continue
                
                doc_ref = self.db.collection(collection).document(doc_id)
                
                if op_type == 'set':
                    batch.set(doc_ref, data)
                elif op_type == 'update':
                    data['updated_at'] = firestore.SERVER_TIMESTAMP
                    batch.update(doc_ref, data)
                elif op_type == 'delete':
                    batch.delete(doc_ref)
                else:
                    results.append({'error': f'Invalid operation type: {op_type}'})
                    continue
                
                results.append({'success': True, 'operation': op_type, 'doc_id': doc_id})
            
            batch.commit()
            
            logger.info(f"Batch operation completed: {len(operations)} operations")
            return self._success_response({
                'operations_count': len(operations),
                'results': results
            }, "Batch operation completed successfully")
            
        except Exception as e:
            return self._handle_error("batch_operation", e)

    def health_check(self) -> Dict[str, Any]:
        """
        Database health check
        """
        try:
            # Simple test query
            test_query = self.db.collection('users').limit(1)
            list(test_query.stream())
            
            return self._success_response({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'firestore'
            }, "Database connection healthy")
            
        except Exception as e:
            return self._handle_error("health_check", e)


# ==================== SECURITY RULES COMMENTS ====================
"""
FIRESTORE SECURITY RULES REQUIREMENTS:

1. USERS Collection:
   - Users can read/write their own profile
   - Admin can read/write any user profile
   - Public can read basic seller profiles (name, rating, etc.)

2. PRODUCTS Collection:
   - Public read access for active products
   - Sellers can write their own products
   - Admin can write any product

3. ORDERS Collection:
   - Customers can read their own orders
   - Sellers can read orders for their products
   - Admin can read any order
   - Only system/admin can create orders

4. CATEGORIES Collection:
   - Public read access
   - Admin write access only

5. INVENTORY Collection:
   - Sellers can read/write inventory for their products
   - Admin can read/write any inventory
   - Warehouse staff can read/write for their warehouse

6. WAREHOUSES Collection:
   - Admin and warehouse staff read/write access
   - Sellers can read warehouse info

7. CARTS Collection:
   - Users can read/write their own cart only

8. REVIEWS Collection:
   - Public read access for approved reviews
   - Users can write reviews for purchased products
   - Users can read/update their own reviews
   - Admin can moderate reviews

9. NOTIFICATIONS Collection:
   - Users can read their own notifications
   - System can create notifications

10. SUPPLIERS Collection:
    - Admin read/write access only
    - Authorized personnel read access

Example Security Rule Structure:
```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      allow read, write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    match /products/{productId} {
      allow read: if resource.data.status == 'active';
      allow write: if request.auth != null && 
        (request.auth.uid == resource.data.seller_id || 
         get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin');
    }
    
    // Add similar rules for other collections...
  }
}
```
"""

# ==================== USAGE EXAMPLE ====================
"""
# Initialize the database handler
db_handler = FirestoreEcommerceDB(project_id='your-project-id')

# Create a user
user_data = {
    'email': 'user@example.com',
    'name': 'John Doe',
    'role': 'customer',
    'address': {
        'street': '123 Main St',
        'city': 'Anytown',
        'state': 'CA',
        'zip': '12345'
    }
}
result = db_handler.create_user_profile(user_data)
print(result)

# Add a product
product_data = {
    'title': 'Sample Product',
    'description': 'This is a sample product',
    'price': 29.99,
    'category_id': 'electronics',
    'seller_id': 'seller_123',
    'inventory_quantity': 100,
    'images': ['image1.jpg', 'image2.jpg']
}
result = db_handler.add_product(product_data)
print(result)

# Get products with filters
filters = {
    'category_id': 'electronics',
    'min_price': 20.0,
    'max_price': 50.0
}
result = db_handler.get_products_with_filters(filters, limit=10)
print(result)

# Create an order
order_data = {
    'customer_id': 'user_123',
    'seller_id': 'seller_123',
    'items': [
        {
            'product_id': 'product_123',
            'quantity': 2,
            'price': 29.99
        }
    ],
    'total_amount': 59.98,
    'shipping_address': user_data['address']
}
result = db_handler.create_order(order_data)
print(result)
"""
                