import sys
import os
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.getcwd())

from backend.utils.helpers import check_is_late

def test_late_logic():
    print("--- Late Entry Logic Verification ---")
    
    out_date = "2026-03-15"
    
    # Case 1: On time
    expected = "18:00:00"
    actual = datetime(2026, 3, 15, 17, 55, 0)
    print(f"Scenario 1 (On Time): {check_is_late(out_date, expected, actual)} (Expected: False)")
    
    # Case 2: Exactly on time
    actual = datetime(2026, 3, 15, 18, 0, 0)
    print(f"Scenario 2 (On Time): {check_is_late(out_date, expected, actual)} (Expected: False)")
    
    # Case 3: Late
    actual = datetime(2026, 3, 15, 18, 0, 1)
    print(f"Scenario 3 (Late):    {check_is_late(out_date, expected, actual)} (Expected: True)")
    
    # Case 4: Return next day (Late)
    actual = datetime(2026, 3, 16, 0, 5, 0)
    print(f"Scenario 4 (Late):    {check_is_late(out_date, expected, actual)} (Expected: True)")
    
    # Case 5: 23:59:00 (Not Returning Today)
    expected = "23:59:00"
    actual = datetime(2026, 3, 16, 1, 0, 0)
    print(f"Scenario 5 (NR Today): {check_is_late(out_date, expected, actual)} (Expected: False)")
    
    # Case 6: Timedelta input
    expected = timedelta(hours=18)
    actual = datetime(2026, 3, 15, 18, 10, 0)
    print(f"Scenario 6 (Late/TD): {check_is_late(out_date, expected, actual)} (Expected: True)")

if __name__ == "__main__":
    test_late_logic()
