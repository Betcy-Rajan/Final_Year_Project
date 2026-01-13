"""
Test script for the RAG Agent - Sample queries
"""
import json
from scheme_rag_agent import SchemeRAGAgent, QueryParser

def test_rag_agent():
    """Test the RAG agent with sample queries"""
    
    print("=" * 80)
    print("Government Scheme RAG Agent - Sample Queries")
    print("=" * 80)
    print()
    
    # Initialize RAG agent
    print("Loading schemes and building vector index...")
    rag_agent = SchemeRAGAgent()
    rag_agent.load_schemes()
    print(f"✓ Loaded {len(rag_agent.schemes)} schemes\n")
    
    # Sample queries
    sample_queries = [
        {
            "query": "I am from Goa and need financial assistance schemes",
            "description": "State + Subcategory query"
        },
        {
            "query": "I'm a small farmer from Rajasthan with 2 acres of land, need schemes for wheat cultivation",
            "description": "State + Land size + Crop query"
        },
        {
            "query": "Show me animal husbandry schemes in Himachal Pradesh",
            "description": "State + Subcategory (semantic search)"
        },
        {
            "query": "I need schemes for dairy farming in Maharashtra",
            "description": "State + Activity (semantic matching)"
        },
        {
            "query": "I'm from Odisha, 35 years old, SC category, need startup schemes",
            "description": "State + Age + Target group + Subcategory"
        },
        {
            "query": "Central schemes for organic farming",
            "description": "Central schemes + Subcategory"
        }
    ]
    
    for i, test_case in enumerate(sample_queries, 1):
        print("-" * 80)
        print(f"Sample Query {i}: {test_case['description']}")
        print(f"Query: \"{test_case['query']}\"")
        print("-" * 80)
        
        try:
            # Parse query
            profile = QueryParser.parse(test_case['query'], context_state=None)
            print(f"\nParsed Profile:")
            print(f"  State: {profile.state}")
            print(f"  Sub-category: {profile.sub_category}")
            print(f"  Crops: {profile.crops}")
            print(f"  Land size: {profile.land_size} acres" if profile.land_size else "  Land size: Not specified")
            print(f"  Age: {profile.age}" if profile.age else "  Age: Not specified")
            print(f"  Target group: {profile.target_group}" if profile.target_group else "  Target group: Not specified")
            print(f"  Scheme scope: {profile.scheme_scope}")
            
            # Retrieve schemes
            print(f"\nRetrieving top 5 schemes...")
            schemes = rag_agent.retrieve_schemes(profile, top_k=5)
            
            # Assess eligibility
            schemes = rag_agent.assess_eligibility(profile, schemes)
            
            print(f"\nFound {len(schemes)} relevant schemes:\n")
            
            for j, scheme in enumerate(schemes, 1):
                scheme_name = scheme.get("scheme_name", "Unknown")
                scheme_state = scheme.get("state", "")
                scheme_type = "Central" if not scheme_state else f"State ({scheme_state})"
                eligibility_status = scheme.get("eligibility_status", "unclear")
                
                print(f"{j}. {scheme_name}")
                print(f"   Type: {scheme_type}")
                print(f"   Eligibility: {eligibility_status}")
                
                # Show brief description
                brief = scheme.get("brief_description", "")
                if brief:
                    print(f"   Description: {brief[:150]}...")
                
                # Show sub-categories
                subcats = scheme.get("sub_category", [])
                if subcats:
                    print(f"   Sub-categories: {', '.join(subcats[:3])}")
                
                print()
            
        except Exception as e:
            print(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    test_rag_agent()

