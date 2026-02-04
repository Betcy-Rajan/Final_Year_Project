"""
AgriMitra Agentic Prototype - Demo Script
Demonstrates the system with predefined test cases
"""
import json
import sys
import os
from workflow import AgriMitraWorkflow
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgriMitraDemo:
    """Demo class to showcase AgriMitra capabilities"""
    
    def __init__(self):
        self.workflow = AgriMitraWorkflow()
    
    def run_demo_queries(self):
        """Run a series of demo queries to showcase the system"""
        
        demo_queries = [
            {
                "query": "My tomato plants have yellow spots on leaves",
                "description": "Disease diagnosis - should trigger disease agent"
            },
            {
                "query": "What's the current price of rice?",
                "description": "Price inquiry - should trigger price agent"
            },
            {
                "query": "My wheat is sick and I want to know the market price",
                "description": "Combined query - should trigger both agents"
            },
            {
                "query": "How to treat powdery mildew on my crops",
                "description": "Direct remedy request - should trigger disease agent"
            },
            {
                "query": "Should I sell my corn now or wait?",
                "description": "Market advice - should trigger price agent"
            }
        ]
        
        print("🌱 AgriMitra Agentic Prototype - Demo Mode")
        print("=" * 60)
        print("This demo showcases the multi-agent coordination and decision-making")
        print("capabilities of the AgriMitra system.\n")
        
        for i, demo in enumerate(demo_queries, 1):
            print(f"\n{'='*60}")
            print(f"DEMO {i}: {demo['description']}")
            print(f"{'='*60}")
            print(f"Query: {demo['query']}")
            print("-" * 60)
            
            try:
                # Run the workflow (no image for demo queries)
                result = self.workflow.run(demo['query'], image_path=None)
                
                # Display the final response
                print(f"\n🌾 AgriMitra Response:")
                print(result.get('final_response', 'No response generated'))
                
                # Show execution summary
                print(f"\n📊 Execution Summary:")
                summary = self.workflow.get_execution_summary(result)
                print(summary)
                
                # Ask if user wants to continue
                if i < len(demo_queries):
                    input("\nPress Enter to continue to next demo...")
                    
            except Exception as e:
                print(f"❌ Error in demo {i}: {e}")
                logger.error(f"Demo {i} error: {e}")
        
        print(f"\n{'='*60}")
        print("🎉 Demo completed!")
        print("The system demonstrated:")
        print("• Intelligent routing based on user intent")
        print("• Multi-agent coordination and tool invocation")
        print("• Comprehensive synthesis of information")
        print("• Graceful error handling and fallback logic")
        print(f"{'='*60}")
    
    def interactive_demo(self):
        """Run an interactive demo where user can input custom queries"""
        print("\n🌱 Interactive Demo Mode")
        print("=" * 40)
        print("Enter your agricultural queries to see the system in action!")
        print("Type 'quit' to exit demo mode.\n")
        
        while True:
            try:
                user_input = input("🌱 Your query: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("👋 Demo mode ended. Thank you!")
                    break
                
                if not user_input:
                    print("⚠️ Please enter a query")
                    continue
                
                print(f"\n🤖 Processing: {user_input}")
                print("-" * 40)
                
                # Run the workflow (check if input is image path)
                image_path = None
                if os.path.exists(user_input) and any(user_input.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp']):
                    image_path = user_input
                    query_text = "Analyze this plant image for disease detection"
                else:
                    query_text = user_input
                
                result = self.workflow.run(query_text, image_path)
                
                # Display response
                print(f"\n🌾 AgriMitra Response:")
                print(result.get('final_response', 'No response generated'))
                
                # Show execution log
                execution_log = result.get('execution_log', [])
                if execution_log:
                    print(f"\n📋 Execution Steps:")
                    for j, step in enumerate(execution_log, 1):
                        print(f"  {j}. {step.get('node', 'unknown')}")
                
                print("\n" + "-" * 40)
                
            except KeyboardInterrupt:
                print("\n👋 Demo interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"Interactive demo error: {e}")

def main():
    """Main demo function"""
    print("Choose demo mode:")
    print("1. Automated demo with predefined queries")
    print("2. Interactive demo with custom queries")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\nEnter choice (1-3): ").strip()
            
            if choice == '1':
                demo = AgriMitraDemo()
                demo.run_demo_queries()
                break
            elif choice == '2':
                demo = AgriMitraDemo()
                demo.interactive_demo()
                break
            elif choice == '3':
                print("👋 Goodbye!")
                break
            else:
                print("⚠️ Please enter 1, 2, or 3")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    main()
