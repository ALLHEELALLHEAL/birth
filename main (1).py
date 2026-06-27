import random

def birth_gate(C, A, B, random0):
    """Simulates the logic gate behavior for inputs (C, A, B)."""
    if (C, A, B) != (0, 0, 0):
        return C & (A ^ B)
    
    # 3-way distribution path
    branch = random.choice(["branch_0", "branch_1", "branch_nested"])
    if branch == "branch_0":
        return 0
    elif branch == "branch_1":
        return 1
    elif branch == "branch_nested":
        return random.choice([random0, 1])

# --- Simulation Configurations ---
TOTAL_CYCLES = 1000000
current_state = 0  # Start gate at 0 (unactivated)

# Tracking metrics
total_ones = 0
total_zeros = 0
consecutive_ones = 0
max_consecutive_ones = 0

print(f"Simulating {TOTAL_CYCLES:,} clock cycles for input state (0, 0, 0)...")

for _ in range(TOTAL_CYCLES):
    # Process current cycle
    output = birth_gate(0, 0, 0, current_state)
    
    if output == 1:
        total_ones += 1
        consecutive_ones += 1
        if consecutive_ones > max_consecutive_ones:
            max_consecutive_ones = consecutive_ones
    else:
        total_zeros += 1
        consecutive_ones = 0
        
    # Feedback loop: pass current output as memory (random0) for next cycle
    current_state = output

# --- Calculate Results ---
pct_ones = (total_ones / TOTAL_CYCLES) * 100
pct_zeros = (total_zeros / TOTAL_CYCLES) * 100

print("\n=== GATE ANALYSIS RESULTS ===")
print(f"Total Time Active (State 1):  {total_ones:,} cycles ({pct_ones:.2f}%)")
print(f"Total Time Inactive (State 0): {total_zeros:,} cycles ({pct_zeros:.2f}%)")
print(f"Longest Unbroken 'Alive' Streak: {max_consecutive_ones:,} cycles")






    