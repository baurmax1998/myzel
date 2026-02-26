"""Test DynamoDB operations"""
import time
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.resources.dynamodb import DynamoDB
from test.resources.env_helper import load_env


def test_dynamodb_operations():
    """Test DynamoDB put_item, get_item, scan, delete_item operations"""
    env = load_env()

    table = DynamoDB(
        table_name="test-myzel-operations-table",
        partition_key={'name': 'id', 'type': 'S'},
        billing_mode="PAY_PER_REQUEST",
        env=env
    )

    try:
        print("=" * 60)
        print("Testing DynamoDB Operations")
        print("=" * 60)

        # Create DynamoDB Table
        print("\n1. Creating DynamoDB Table...")
        table_arn = table.create()
        print(f"✓ Table created: {table_arn}")
        time.sleep(5)

        # Test put_item
        print("\n2. Testing put_item...")
        test_item = {
            'id': 'test-001',
            'title': 'Test Todo',
            'completed': False,
            'description': 'This is a test item'
        }
        table.put_item(test_item)
        print(f"✓ Item added")
        time.sleep(1)

        # Test get_item
        print("\n3. Testing get_item...")
        retrieved_item = table.get_item({'id': 'test-001'})
        assert retrieved_item is not None, "Item should be found"
        assert retrieved_item['id'] == 'test-001', f"Expected id 'test-001', got {retrieved_item['id']}"
        assert retrieved_item['title'] == 'Test Todo', f"Expected title 'Test Todo', got {retrieved_item['title']}"
        print(f"✓ Item retrieved: {retrieved_item}")

        # Test put multiple items
        print("\n4. Testing put_item (multiple)...")
        for i in range(2, 5):
            table.put_item({
                'id': f'test-{i:03d}',
                'title': f'Todo {i}',
                'completed': i % 2 == 0
            })
        print(f"✓ 3 more items added")
        time.sleep(1)

        # Test scan
        print("\n5. Testing scan...")
        items = table.scan()
        assert isinstance(items, list), "scan() should return a list"
        assert len(items) == 4, f"Expected 4 items, got {len(items)}"
        print(f"✓ Scan successful: {len(items)} items")
        for item in items:
            print(f"  - {item['id']}: {item.get('title', 'N/A')}")

        # Test query (if table has sort key, this would be more complex)
        print("\n6. Testing get_item (non-existent)...")
        non_existent = table.get_item({'id': 'non-existent'})
        assert non_existent is None, "Non-existent item should return None"
        print(f"✓ Non-existent item handled correctly")

        # Test delete_item
        print("\n7. Testing delete_item...")
        table.delete_item({'id': 'test-001'})
        print(f"✓ Item deleted")
        time.sleep(1)

        # Verify deletion
        print("\n8. Verifying deletion...")
        deleted_item = table.get_item({'id': 'test-001'})
        assert deleted_item is None, "Deleted item should not be found"
        print(f"✓ Deletion verified")

        # Test scan after deletion
        print("\n9. Testing scan (after deletion)...")
        items = table.scan()
        assert len(items) == 3, f"Expected 3 items, got {len(items)}"
        print(f"✓ Scan successful: {len(items)} items remaining")

        print("\n✓ All DynamoDB operation tests passed!")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup DynamoDB Table
        print("\n10. Cleaning up DynamoDB Table...")
        try:
            # First delete all items
            print("   Deleting all items...")
            items = table.scan()
            for item in items:
                table.delete_item({'id': item['id']})
            time.sleep(2)

            # Then delete table
            table.delete(table_arn)
            print("✓ Table deleted")
        except Exception as e:
            print(f"Warning: Could not delete table: {e}")


if __name__ == "__main__":
    test_dynamodb_operations()
