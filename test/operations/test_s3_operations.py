"""Test S3 operations"""
import tempfile
import time
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.resources.s3 import S3
from test.resources.env_helper import load_env


def test_s3_operations():
    """Test S3 list, upload, download, delete operations"""
    env = load_env()

    bucket = S3(
        bucket_name="test-myzel-operations-bucket",
        env=env,
        policy={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::test-myzel-operations-bucket/*"
            }]
        }
    )

    try:
        print("=" * 60)
        print("Testing S3 Operations")
        print("=" * 60)

        # Create S3 Bucket
        print("\n1. Creating S3 Bucket...")
        bucket_arn = bucket.create()
        print(f"✓ Bucket created: {bucket_arn}")
        time.sleep(2)

        # Test list (should be empty)
        print("\n2. Testing list (empty bucket)...")
        objects = bucket.list()
        assert isinstance(objects, list), "list() should return a list"
        assert len(objects) == 0, f"Expected empty bucket, got {len(objects)} objects"
        print(f"✓ List successful: {len(objects)} objects")

        # Test upload
        print("\n3. Testing upload...")
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test content for S3")
            temp_file = f.name

        try:
            bucket.upload(temp_file, "test/file.txt")
            print(f"✓ Upload successful")
            time.sleep(1)

            # Test list (should have 1 object)
            print("\n4. Testing list (after upload)...")
            objects = bucket.list()
            assert len(objects) == 1, f"Expected 1 object, got {len(objects)}"
            assert objects[0] == "test/file.txt", f"Expected 'test/file.txt', got {objects[0]}"
            print(f"✓ List successful: {objects}")

            # Test download
            print("\n5. Testing download...")
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                download_file = f.name

            bucket.download("test/file.txt", download_file)
            with open(download_file, 'r') as f:
                content = f.read()
            assert content == "Test content for S3", f"Downloaded content mismatch: {content}"
            print(f"✓ Download successful: {content}")

            # Test delete
            print("\n6. Testing delete...")
            bucket.delete("test/file.txt")
            print(f"✓ Delete successful")
            time.sleep(1)

            # Test list (should be empty again)
            print("\n7. Testing list (after delete)...")
            objects = bucket.list()
            assert len(objects) == 0, f"Expected empty bucket, got {len(objects)} objects"
            print(f"✓ List successful: {len(objects)} objects")

            print("\n✓ All S3 operation tests passed!")

        finally:
            # Cleanup temp files
            Path(temp_file).unlink(missing_ok=True)
            Path(download_file).unlink(missing_ok=True)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup S3 Bucket
        print("\n8. Cleaning up S3 Bucket...")
        try:
            bucket.delete("")  # Clear bucket first
        except:
            pass

        try:
            bucket.delete(bucket_arn)
            print("✓ Bucket deleted")
        except Exception as e:
            print(f"Warning: Could not delete bucket: {e}")


if __name__ == "__main__":
    test_s3_operations()
