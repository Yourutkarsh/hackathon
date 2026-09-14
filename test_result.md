#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

## user_problem_statement: "Sentinel Shift V5.1 Compliance Hardening — implement Tier 1/2/3 fixes without changing the immutable engine."
## backend:
##   - task: "Tier 1: scenario taxonomy (PROJECT_CHANGE, MIXED_CASE, BENIGN->NORMAL), strict spec detection (70+), revised ablations"
##     implemented: true
##     working: true
##     file: "backend/sentinel/fixtures.py, scoring.py, lifecycle.py"
##     priority: "high"
##     status_history:
##         - working: true
##         - agent: "main"
##         - comment: "test_v51_boundaries.py -> ALL_V51_BOUNDARY_TESTS_PASSED; Rahul E6 verified 67.98 ELEVATED (legacy-detected, below strict 70 bar); PROJECT_CHANGE e5 27.94 NORMAL (settles); MIXED_CASE e4 65.37 ELEVATED."
##   - task: "Tier 2: Isolation Forest adapter (iforest-v1) + baseline lifecycle/version + calibration sweep"
##     implemented: true
##     working: true
##     file: "backend/sentinel/iforest.py, lifecycle.py, calibration.py, demo_db.py"
##     priority: "high"
##     status_history:
##         - working: true
##         - agent: "main"
##         - comment: "Fallback/unavailable/q99==q95/determinism covered; baseline_version increments 1..N across resets; calibration reporting-only with empty-slice + deterministic tie-break tests."
##   - task: "Tier 3: assistant schema aliases + backward-compatible aliases"
##     implemented: true
##     working: true
##     file: "backend/sentinel/service.py"
##     priority: "medium"
##     status_history:
##         - working: true
##         - agent: "main"
##         - comment: "recommended_investigation_steps/evidence_ids/signal_families added; legacy recommended_steps/citations retained; BENIGN scenario alias + legacy ablation names + legacy detection metrics exposed."
## frontend:
##   - task: "Baseline lifecycle, iforest metadata, revised ablation/calibration, updated assistant fields"
##     implemented: true
##     working: true
##     file: "frontend/src/components/soc/BaselineLifecycle.jsx, ModelMetadata.jsx, EvaluationPanel.jsx, AssistantDrawer.jsx, SocWorkspace.jsx, lib/severity.js"
##     priority: "high"
##     status_history:
##         - working: true
##         - agent: "main"
##         - comment: "All changed JSX validated with esbuild (exit 0). Manual flow reset -> Rahul E6 -> investigate verified against the API; populations show COLD/WARMING/READY."
## metadata:
##   created_by: "main_agent"
##   version: "1.1"
##   run_ui: false
## test_plan:
##   current_focus:
##     - "Re-run python test_v51_fixes.py, python test_phase1_persistence.py, python test_v51_boundaries.py after any change."
## agent_communication:
##   - agent: "main"
##     message: "Engine preserved byte-for-byte (sha256 matches ENGINE_MANIFEST.json, chmod 444). test_v51_fixes.py unchanged (sha256 verified). No live external LLM added."
##   - agent: "main"
##     message: "Added test_api_routes.py (FastAPI TestClient): 47 checks across all /api routes -> ALL_API_ROUTE_TESTS_PASSED. requirements.txt adds scikit-learn + httpx."
##   - agent: "main"
##     message: "sentinel-guard: added test_sentinel_invariants.py (engine immutability, zero temporal leakage sweep over every baseline, read-only LLM separation, deterministic reproducibility) -> ALL_SENTINEL_INVARIANTS_SATISFIED. Also moved the baseline_version bump inside the timed reset region so the <50 ms target is measured honestly. All 5 suites green."