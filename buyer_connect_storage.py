"""
Firebase Firestore storage for Buyer Connect module
Stores buyer details, listings, and matches in Firebase Firestore
"""
from typing import List, Dict, Optional, Union
from buyer_connect_models import (
    Buyer, FarmerListing, BuyerMatch, MatchStatus, ListingStatus, CropInterest,
    BuyerRequirement, Negotiation
)
import logging
import os
from datetime import datetime
import json

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("firebase-admin not installed. Install with: pip install firebase-admin")

logger = logging.getLogger(__name__)


def _initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not FIREBASE_AVAILABLE:
        raise ImportError("firebase-admin is not installed. Install with: pip install firebase-admin")
    
    # Check if Firebase is already initialized
    try:
        firebase_admin.get_app()
        logger.info("Firebase already initialized")
        return firestore.client()
    except ValueError:
        # Firebase not initialized yet
        pass
    
    # Try to initialize Firebase
    # Option 1: Use service account JSON file
    firebase_credentials_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
    if firebase_credentials_path and os.path.exists(firebase_credentials_path):
        cred = credentials.Certificate(firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        logger.info(f"Firebase initialized with credentials from {firebase_credentials_path}")
    else:
        # Option 2: Use environment variable with JSON string
        firebase_credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
        if firebase_credentials_json:
            cred_dict = json.loads(firebase_credentials_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with credentials from environment variable")
        else:
            # Option 3: Use default credentials (for Google Cloud environments)
            try:
                firebase_admin.initialize_app()
                logger.info("Firebase initialized with default credentials")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}")
                raise RuntimeError(
                    "Firebase initialization failed. Please set FIREBASE_CREDENTIALS_PATH "
                    "or FIREBASE_CREDENTIALS_JSON environment variable, or use default credentials."
                ) from e
    
    return firestore.client()


class BuyerConnectStorage:
    """Firebase Firestore storage for buyer connect data"""
    
    def __init__(self):
        if not FIREBASE_AVAILABLE:
            raise ImportError("firebase-admin is not installed. Install with: pip install firebase-admin")
        
        try:
            self.db = _initialize_firebase()
            self.buyers_collection = self.db.collection('buyers')
            self.listings_collection = self.db.collection('farmer_listings')  # Updated collection name
            self.matches_collection = self.db.collection('matches')
            self.buyer_requirements_collection = self.db.collection('buyer_requirements')  # New collection
            self.negotiations_collection = self.db.collection('negotiations')  # New collection
            
            # Initialize with demo data if collections are empty
            self._init_demo_data_if_needed()
            logger.info("BuyerConnectStorage initialized with Firebase Firestore")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase storage: {e}")
            raise
    
    def _init_demo_data_if_needed(self):
        """Initialize with demo buyers if the buyers collection is empty"""
        try:
            buyers_snapshot = self.buyers_collection.limit(1).get()
            if len(buyers_snapshot) == 0:
                logger.info("Buyers collection is empty, initializing demo data...")
                self._init_demo_data()
        except Exception as e:
            logger.warning(f"Could not check if demo data is needed: {e}")
    
    def _init_demo_data(self):
        """Initialize with demo buyers for testing"""
        demo_buyers = [
            Buyer(
                id=None,  # Will be set by Firestore
                name="GreenGrow Traders",
                phone="+91-9876543210",
                location="Pune",
                interested_crops=[
                    CropInterest(crop="tomato", min_qty=100, max_qty=1000, preferred_price=32),
                    CropInterest(crop="potato", min_qty=200, max_qty=2000, preferred_price=20),
                ],
                verified=True
            ),
            Buyer(
                id=None,
                name="FreshFarm Co.",
                phone="+91-9876543211",
                location="Mumbai",
                interested_crops=[
                    CropInterest(crop="rice", min_qty=500, max_qty=5000, preferred_price=15),
                    CropInterest(crop="wheat", min_qty=300, max_qty=3000, preferred_price=12),
                ],
                verified=True
            ),
            Buyer(
                id=None,
                name="AgriMarket Solutions",
                phone="+91-9876543212",
                location="Delhi",
                interested_crops=[
                    CropInterest(crop="tomato", min_qty=50, max_qty=500, preferred_price=30),
                    CropInterest(crop="onion", min_qty=100, max_qty=1000, preferred_price=35),
                ],
                verified=False
            ),
        ]
        
        for buyer in demo_buyers:
            self._create_buyer_in_firestore(buyer)
        
        logger.info(f"Initialized {len(demo_buyers)} demo buyers in Firebase")
    
    def _buyer_to_dict(self, buyer: Buyer) -> Dict:
        """Convert Buyer model to Firestore-compatible dictionary"""
        buyer_dict = buyer.model_dump(exclude={'id'}, exclude_none=True)
        # Convert interested_crops to list of dicts
        if 'interested_crops' in buyer_dict:
            buyer_dict['interested_crops'] = [
                crop.model_dump() if hasattr(crop, 'model_dump') else crop
                for crop in buyer_dict['interested_crops']
            ]
        return buyer_dict
    
    def _dict_to_buyer(self, doc_id: str, data: Dict) -> Buyer:
        """Convert Firestore document to Buyer model"""
        data['id'] = int(doc_id) if doc_id.isdigit() else doc_id
        # Convert interested_crops from dicts to CropInterest models
        if 'interested_crops' in data:
            data['interested_crops'] = [
                CropInterest(**crop) if isinstance(crop, dict) else crop
                for crop in data['interested_crops']
            ]
        return Buyer(**data)
    
    def _listing_to_dict(self, listing: FarmerListing) -> Dict:
        """Convert FarmerListing model to Firestore-compatible dictionary"""
        listing_dict = listing.model_dump(exclude={'id'}, exclude_none=True)
        # Convert datetime to ISO format string for Firestore
        if 'created_at' in listing_dict and listing_dict['created_at']:
            if isinstance(listing_dict['created_at'], datetime):
                listing_dict['created_at'] = listing_dict['created_at'].isoformat()
        # Convert Enum to string
        if 'status' in listing_dict:
            listing_dict['status'] = listing_dict['status'].value if hasattr(listing_dict['status'], 'value') else str(listing_dict['status'])
        return listing_dict
    
    def _dict_to_listing(self, doc_id: str, data: Dict) -> FarmerListing:
        """Convert Firestore document to FarmerListing model"""
        # Keep as string if not a pure digit, otherwise try to convert
        # But Firestore IDs are usually strings, so keep as string
        data['id'] = doc_id  # Keep as string for Firestore compatibility
        # Convert ISO string to datetime
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
        # Convert string to Enum
        if 'status' in data:
            data['status'] = ListingStatus(data['status'])
        return FarmerListing(**data)
    
    def _match_to_dict(self, match: BuyerMatch) -> Dict:
        """Convert BuyerMatch model to Firestore-compatible dictionary"""
        match_dict = match.model_dump(exclude={'id'}, exclude_none=True)
        # Convert datetime to ISO format string
        if 'created_at' in match_dict and match_dict['created_at']:
            if isinstance(match_dict['created_at'], datetime):
                match_dict['created_at'] = match_dict['created_at'].isoformat()
        # Convert Enum to string
        if 'match_status' in match_dict:
            match_dict['match_status'] = match_dict['match_status'].value if hasattr(match_dict['match_status'], 'value') else str(match_dict['match_status'])
        return match_dict
    
    def _dict_to_match(self, doc_id: str, data: Dict) -> BuyerMatch:
        """Convert Firestore document to BuyerMatch model"""
        data['id'] = int(doc_id) if doc_id.isdigit() else doc_id
        # Convert ISO string to datetime
        if 'created_at' in data and data['created_at']:
            if isinstance(data['created_at'], str):
                data['created_at'] = datetime.fromisoformat(data['created_at'])
        # Convert string to Enum
        if 'match_status' in data:
            data['match_status'] = MatchStatus(data['match_status'])
        return BuyerMatch(**data)
    
    def _create_buyer_in_firestore(self, buyer: Buyer) -> Buyer:
        """Create a buyer in Firestore and return with ID"""
        buyer_dict = self._buyer_to_dict(buyer)
        doc_ref = self.buyers_collection.add(buyer_dict)[1]
        # Get the auto-generated ID
        buyer_id = doc_ref.id
        # Try to use numeric ID if possible, otherwise use string ID
        try:
            buyer_id_int = int(buyer_id)
            buyer.id = buyer_id_int
        except ValueError:
            buyer.id = buyer_id
        return buyer
    
    def create_listing(self, listing: FarmerListing) -> FarmerListing:
        """Create a new farmer listing in Firestore"""
        listing_dict = self._listing_to_dict(listing)
        doc_ref = self.listings_collection.add(listing_dict)[1]
        # Keep Firestore document ID as string (Firestore uses string IDs)
        listing.id = doc_ref.id
        logger.info(f"Created listing {listing.id} for farmer {listing.farmer_id} in Firebase")
        return listing
    
    def get_listing(self, listing_id) -> Optional[FarmerListing]:
        """Get a listing by ID from Firestore (accepts int or string)"""
        try:
            listing_id_str = str(listing_id)
            doc_ref = self.listings_collection.document(listing_id_str)
            doc = doc_ref.get()
            if doc.exists:
                return self._dict_to_listing(listing_id_str, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting listing {listing_id}: {e}")
            return None
    
    def get_all_buyers(self) -> List[Buyer]:
        """Get all buyers from Firestore"""
        try:
            buyers = []
            buyers_snapshot = self.buyers_collection.stream()
            for doc in buyers_snapshot:
                buyer = self._dict_to_buyer(doc.id, doc.to_dict())
                buyers.append(buyer)
            return buyers
        except Exception as e:
            logger.error(f"Error getting all buyers: {e}")
            return []
    
    def get_buyer(self, buyer_id) -> Optional[Buyer]:
        """Get a buyer by ID from Firestore (accepts int or string)"""
        try:
            buyer_id_str = str(buyer_id)
            doc_ref = self.buyers_collection.document(buyer_id_str)
            doc = doc_ref.get()
            if doc.exists:
                return self._dict_to_buyer(buyer_id_str, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting buyer {buyer_id}: {e}")
            return None
    
    def create_buyer(self, buyer: Buyer) -> Buyer:
        """Create a new buyer in Firestore"""
        return self._create_buyer_in_firestore(buyer)
    
    def create_match(self, match: BuyerMatch) -> BuyerMatch:
        """Create a new buyer match in Firestore"""
        match_dict = self._match_to_dict(match)
        doc_ref = self.matches_collection.add(match_dict)[1]
        match.id = int(doc_ref.id) if doc_ref.id.isdigit() else doc_ref.id
        logger.info(f"Created match {match.id} for listing {match.listing_id} and buyer {match.buyer_id} in Firebase")
        return match
    
    def get_match(self, match_id) -> Optional[BuyerMatch]:
        """Get a match by ID from Firestore (accepts int or string)"""
        try:
            match_id_str = str(match_id)
            doc_ref = self.matches_collection.document(match_id_str)
            doc = doc_ref.get()
            if doc.exists:
                return self._dict_to_match(match_id_str, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting match {match_id}: {e}")
            return None
    
    def update_match_status(self, match_id, status: MatchStatus) -> Optional[BuyerMatch]:
        """Update match status in Firestore (accepts int or string)"""
        try:
            match_id_str = str(match_id)
            doc_ref = self.matches_collection.document(match_id_str)
            doc_ref.update({'match_status': status.value})
            logger.info(f"Updated match {match_id} status to {status.value} in Firebase")
            # Return updated match
            return self.get_match(match_id)
        except Exception as e:
            logger.error(f"Error updating match {match_id} status: {e}")
            return None
    
    def get_matches_for_listing(self, listing_id) -> List[BuyerMatch]:
        """Get all matches for a listing from Firestore (accepts int or string)"""
        try:
            matches = []
            listing_id_str = str(listing_id)
            matches_query = self.matches_collection.where('listing_id', '==', listing_id).stream()
            for doc in matches_query:
                match = self._dict_to_match(doc.id, doc.to_dict())
                matches.append(match)
            return matches
        except Exception as e:
            logger.error(f"Error getting matches for listing {listing_id}: {e}")
            return []
    
    def update_listing_status(self, listing_id, status: ListingStatus) -> Optional[FarmerListing]:
        """Update listing status in Firestore (accepts int or string)"""
        try:
            listing_id_str = str(listing_id)
            doc_ref = self.listings_collection.document(listing_id_str)
            doc_ref.update({'status': status.value})
            logger.info(f"Updated listing {listing_id} status to {status.value} in Firebase")
            # Return updated listing
            return self.get_listing(listing_id)
        except Exception as e:
            logger.error(f"Error updating listing {listing_id} status: {e}")
            return None
    
    # Buyer Requirements Methods
    def create_buyer_requirement(self, requirement: BuyerRequirement) -> BuyerRequirement:
        """Create a new buyer requirement in Firestore"""
        try:
            req_dict = requirement.model_dump(exclude={'id'}, exclude_none=True)
            # Ensure buyer_id is stored as integer if it's a numeric string
            if 'buyer_id' in req_dict and isinstance(req_dict['buyer_id'], str) and req_dict['buyer_id'].isdigit():
                req_dict['buyer_id'] = int(req_dict['buyer_id'])
            elif 'buyer_id' in req_dict and isinstance(req_dict['buyer_id'], str) and req_dict['buyer_id'].startswith('buyer'):
                # Convert "buyer1" to 1
                try:
                    req_dict['buyer_id'] = int(req_dict['buyer_id'].replace('buyer', ''))
                except:
                    pass  # Keep as-is if conversion fails
            doc_ref = self.buyer_requirements_collection.add(req_dict)[1]
            requirement.id = doc_ref.id
            logger.info(f"Created buyer requirement {requirement.id} for buyer {req_dict.get('buyer_id')} in Firebase")
            return requirement
        except Exception as e:
            logger.error(f"Error creating buyer requirement: {e}")
            raise
    
    def get_buyer_requirement(self, requirement_id: str) -> Optional[BuyerRequirement]:
        """Get a buyer requirement by ID"""
        try:
            doc_ref = self.buyer_requirements_collection.document(requirement_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return BuyerRequirement(**data)
            return None
        except Exception as e:
            logger.error(f"Error getting buyer requirement {requirement_id}: {e}")
            return None
    
    def get_buyer_requirements(self, buyer_id: Optional[Union[int, str]] = None) -> List[BuyerRequirement]:
        """Get all buyer requirements, optionally filtered by buyer_id"""
        try:
            requirements = []
            if buyer_id is not None:
                # Convert to int if it's a string that can be converted, otherwise use as-is
                if isinstance(buyer_id, str) and buyer_id.isdigit():
                    buyer_id_filter = int(buyer_id)
                else:
                    buyer_id_filter = buyer_id
                query = self.buyer_requirements_collection.where('buyer_id', '==', buyer_id_filter)
            else:
                query = self.buyer_requirements_collection
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                # Ensure buyer_id is properly typed
                if 'buyer_id' in data and isinstance(data['buyer_id'], str) and data['buyer_id'].isdigit():
                    data['buyer_id'] = int(data['buyer_id'])
                requirements.append(BuyerRequirement(**data))
            return requirements
        except Exception as e:
            logger.error(f"Error getting buyer requirements: {e}")
            return []
    
    def update_buyer_requirement(self, requirement_id: str, requirement: BuyerRequirement) -> Optional[BuyerRequirement]:
        """Update a buyer requirement"""
        try:
            req_dict = requirement.model_dump(exclude={'id'}, exclude_none=True)
            doc_ref = self.buyer_requirements_collection.document(requirement_id)
            doc_ref.update(req_dict)
            logger.info(f"Updated buyer requirement {requirement_id} in Firebase")
            return self.get_buyer_requirement(requirement_id)
        except Exception as e:
            logger.error(f"Error updating buyer requirement {requirement_id}: {e}")
            return None
    
    def delete_buyer_requirement(self, requirement_id: str) -> bool:
        """Delete a buyer requirement"""
        try:
            doc_ref = self.buyer_requirements_collection.document(requirement_id)
            doc_ref.delete()
            logger.info(f"Deleted buyer requirement {requirement_id} from Firebase")
            return True
        except Exception as e:
            logger.error(f"Error deleting buyer requirement {requirement_id}: {e}")
            return False
    
    # Negotiation Methods
    def create_negotiation(self, negotiation: Negotiation) -> Negotiation:
        """Create a new negotiation record in Firestore"""
        try:
            neg_dict = negotiation.model_dump(exclude={'id'}, exclude_none=True)
            doc_ref = self.negotiations_collection.add(neg_dict)[1]
            negotiation.id = doc_ref.id
            logger.info(f"Created negotiation {negotiation.id} in Firebase")
            return negotiation
        except Exception as e:
            logger.error(f"Error creating negotiation: {e}")
            raise
    
    def get_negotiation(self, negotiation_id: str) -> Optional[Negotiation]:
        """Get a negotiation by ID"""
        try:
            doc_ref = self.negotiations_collection.document(negotiation_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Negotiation(**data)
            return None
        except Exception as e:
            logger.error(f"Error getting negotiation {negotiation_id}: {e}")
            return None
    
    def get_negotiations_for_listing(self, listing_id: str) -> List[Negotiation]:
        """Get all negotiations for a listing"""
        try:
            negotiations = []
            query = self.negotiations_collection.where('listing_id', '==', listing_id)
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                negotiations.append(Negotiation(**data))
            return negotiations
        except Exception as e:
            logger.error(f"Error getting negotiations for listing {listing_id}: {e}")
            return []
    
    def get_negotiations_for_buyer(self, buyer_id: str) -> List[Negotiation]:
        """Get all negotiations for a buyer"""
        try:
            negotiations = []
            query = self.negotiations_collection.where('buyer_id', '==', buyer_id)
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                negotiations.append(Negotiation(**data))
            return negotiations
        except Exception as e:
            logger.error(f"Error getting negotiations for buyer {buyer_id}: {e}")
            return []
    
    def update_negotiation_decision(self, negotiation_id: str, decision: str) -> Optional[Negotiation]:
        """Update negotiation decision (accept, counter, reject)"""
        try:
            doc_ref = self.negotiations_collection.document(negotiation_id)
            doc_ref.update({
                'decision': decision,
                'timestamp': datetime.now().isoformat()
            })
            logger.info(f"Updated negotiation {negotiation_id} decision to {decision} in Firebase")
            return self.get_negotiation(negotiation_id)
        except Exception as e:
            logger.error(f"Error updating negotiation {negotiation_id} decision: {e}")
            return None


# Global storage instance
try:
    storage = BuyerConnectStorage()
except Exception as e:
    logger.error(f"Failed to initialize Firebase storage: {e}")
    logger.warning("Falling back to in-memory storage. Please configure Firebase credentials.")
    # Fallback to a minimal in-memory storage if Firebase fails
    class FallbackStorage:
        def __init__(self):
            self.buyers = {}
            self.listings = {}
            self.matches = {}
            logger.warning("Using fallback in-memory storage. Data will not persist.")
        
        def get_all_buyers(self):
            return list(self.buyers.values())
        
        def get_buyer(self, buyer_id):
            return self.buyers.get(buyer_id)
        
        def get_listing(self, listing_id):
            return self.listings.get(listing_id)
        
        def create_listing(self, listing):
            listing.id = len(self.listings) + 1
            self.listings[listing.id] = listing
            return listing
        
        def create_match(self, match):
            match.id = len(self.matches) + 1
            self.matches[match.id] = match
            return match
        
        def get_match(self, match_id):
            return self.matches.get(match_id)
        
        def update_match_status(self, match_id, status):
            match = self.matches.get(match_id)
            if match:
                match.match_status = status
            return match
        
        def get_matches_for_listing(self, listing_id):
            return [m for m in self.matches.values() if m.listing_id == listing_id]
        
        def update_listing_status(self, listing_id, status):
            listing = self.listings.get(listing_id)
            if listing:
                listing.status = status
            return listing
    
    storage = FallbackStorage()
