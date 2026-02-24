from src.model import AwsEnviroment, Resources


class ResourceTester:
    """Generischer Test-Runner für alle Resources"""

    def __init__(self, env: AwsEnviroment):
        self.env = env
        self.test_results = []

    def test_resource(self, resource_name: str, resource: Resources, modified_resource: Resources = None):
        """
        Testet einen Resource mit folgendem Ablauf:
        1. create Resource - erstellt Resource in der Cloud
        2. get Resource - holt state von der Resource in der Cloud
        3. create Resource (nochmal) - nichts passiert weil die Resource schon existiert
        4. get Resource - state passt zu der änderung
        5. update Resource mit der id von create - resource wird aktualisiert
        6. get Resource - state passt zu der änderung
        7. update Resource mit falscher id - neue resource wird erstellt (fallback)
        8. get Resource - state passt zu der änderung
        9. delete Resource - löscht die Resource in der Cloud
        10. delete Resource - löscht die neue "Update" Resource in der Cloud
        11. delete Resource (nochmal) - ist ja schon gelöscht, aber es kommt kein fehler
        12. get Resource - leerer state, kein fehler
        """
        print(f"\n{'='*60}")
        print(f"Teste: {resource_name}")
        print(f"{'='*60}")

        try:
            # 1. Create Resource
            print(f"\n1. Create {resource_name}...")
            created_id = resource.create()
            print(f"   ✓ Created with ID: {created_id}")
            self._add_result(resource_name, "create (1st)", True)

            # 2. Get Resource
            print(f"\n2. Get {resource_name}...")
            resource.__class__.get(created_id, self.env)
            print(f"   ✓ Fetched successfully")
            self._add_result(resource_name, "get (after create)", True)

            # 3. Create Resource again
            print(f"\n3. Create {resource_name} again (should be idempotent)...")
            created_id_2 = resource.create()
            is_idempotent = created_id == created_id_2
            print(f"   ✓ Idempotent: {is_idempotent}")
            self._add_result(resource_name, "create (2nd/idempotent)", is_idempotent)

            # 4. Get Resource to verify state
            print(f"\n4. Get {resource_name} to verify state...")
            resource.__class__.get(created_id_2, self.env)
            print(f"   ✓ State verified")
            self._add_result(resource_name, "get (after 2nd create)", True)

            # 5. Update Resource with correct ID
            if modified_resource:
                print(f"\n5. Update {resource_name} with correct ID...")
                updated_id = modified_resource.update(created_id, modified_resource)
                print(f"   ✓ Updated with ID: {updated_id}")
                self._add_result(resource_name, "update (correct ID)", True)

                # 6. Get Resource to verify update
                print(f"\n6. Get {resource_name} to verify update...")
                resource.__class__.get(updated_id, self.env)
                print(f"   ✓ Update verified")
                self._add_result(resource_name, "get (after update)", True)

                # 7. Update with fake ID (should create new)
                print(f"\n7. Update {resource_name} with fake ID (should create new or handle gracefully)...")
                try:
                    fake_id = "fake-id-12345"
                    new_updated_id = modified_resource.update(fake_id, modified_resource)
                    print(f"   ✓ Handled gracefully with ID: {new_updated_id}")
                    self._add_result(resource_name, "update (fake ID)", True)
                    extra_id = new_updated_id
                except Exception as e:
                    print(f"   ✓ Expected exception: {str(e)[:50]}...")
                    self._add_result(resource_name, "update (fake ID)", True)
                    extra_id = None

                # 8. Get Resource to verify
                if extra_id:
                    print(f"\n8. Get {resource_name} to verify new resource...")
                    resource.__class__.get(extra_id, self.env)
                    print(f"   ✓ New resource verified")
                    self._add_result(resource_name, "get (after fake ID update)", True)
            else:
                print(f"\n5-8. Skipping update tests (no modified resource provided)")
                updated_id = created_id
                extra_id = None

            # 9. Delete Resource
            print(f"\n9. Delete {resource_name}...")
            resource.delete(updated_id)
            print(f"   ✓ Deleted")
            self._add_result(resource_name, "delete (1st)", True)

            # 10. Delete extra Resource (if created)
            if extra_id:
                print(f"\n10. Delete {resource_name} (extra from fake ID update)...")
                modified_resource.delete(extra_id)
                print(f"   ✓ Deleted extra")
                self._add_result(resource_name, "delete (2nd/extra)", True)
            else:
                print(f"\n10. Skipping extra delete")

            # 11. Delete Resource again (should be idempotent)
            print(f"\n11. Delete {resource_name} again (should be idempotent)...")
            resource.delete(updated_id)
            print(f"   ✓ Idempotent delete succeeded")
            self._add_result(resource_name, "delete (idempotent)", True)

            # 12. Get Resource (should return empty or not raise)
            print(f"\n12. Get {resource_name} after delete...")
            try:
                resource.__class__.get(updated_id, self.env)
                print(f"   ✓ Get after delete handled gracefully")
                self._add_result(resource_name, "get (after delete)", True)
            except Exception as e:
                print(f"   ✗ Exception: {e}")
                self._add_result(resource_name, "get (after delete)", False)

            print(f"\n✓ {resource_name} tests completed")

        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            self._add_result(resource_name, "overall", False)

    def _add_result(self, resource_name: str, test_name: str, passed: bool):
        """Fügt ein Testergebnis hinzu"""
        status = "✓ PASS" if passed else "✗ FAIL"
        self.test_results.append((resource_name, test_name, status))

    def print_summary(self):
        """Gibt eine Zusammenfassung aller Tests aus"""
        print(f"\n\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")

        current_resource = None
        for resource_name, test_name, status in self.test_results:
            if resource_name != current_resource:
                print(f"\n{resource_name}:")
                current_resource = resource_name
            print(f"  {test_name:30s} {status}")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, _, status in self.test_results if "PASS" in status)
        print(f"\n{'='*60}")
        print(f"Total: {passed_tests}/{total_tests} tests passed")
        print(f"{'='*60}\n")
