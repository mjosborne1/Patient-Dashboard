Plan: Airport Screen for Task Fulfilment

Objective
- New airport screen that lets users select a pathology or radiology organisation, lists patients with requested tasks for that organisation, shows ServiceRequest details per task, and bulk-updates child task statuses.

Backend
- Add route to render screen (e.g., GET /airport).
- Add API: GET /api/organisations/with-tasks -> queries Task with _tag=fulfilment-task-group&_include=Task:owner to extract unique organisations; caches or returns list for dropdown.
- Add API: GET /api/tasks/by-org -> queries Task with owner:Organization.identifier=<selected>, status=requested, _include=Task:focus; supports pagination (offset/limit or _getpagesoffset); groups by patient; returns {tasks[], totalCount, pageSize, offset}.
- Add API: POST /api/task-groups/{groupId}/status -> validates transition from current to target status against allowed state machine; warns if illegal; if valid, sets all child tasks to new status; returns refreshed tasks or error with reason.
- Reuse FHIR client helpers; normalize patient refs, map Task focus to ServiceRequest; handle missing includes by fetching ServiceRequest/<id> if needed.
- Task status transitions: maintain state machine (e.g., requested -> accepted|cancelled; accepted -> in-progress|completed|failed; in-progress -> completed|failed; terminal: completed, failed, cancelled). Enforce on bulk update; reject with message if not allowed.

Frontend
- New template (airport.html) with organisation dropdown auto-populated by GET /api/organisations/with-tasks (no manual entry needed; list is dynamic from server).
- Task table showing patient, group task status, ServiceRequest description/code, and actions; includes pagination controls (Previous/Next, offset display).
- "Details" button per row loads a side panel with ServiceRequest details (from included focus or a follow-up fetch).
- Bulk status select on group task shows allowed transition options only (via status machine on backend or data attr); on selection, POST to /api/task-groups/{groupId}/status; if invalid transition, show warning toast instead of allowing submit.
- Use HTMX for data pulls/swaps; show loading indicators; disable controls during requests; show toast on errors and transition warnings.

Data Flow
- Page load: GET /api/organisations/with-tasks -> dropdown populated with orgs from group task owners.
- Org change triggers GET /api/tasks/by-org?org=<identifier>&offset=0&limit=20 with status=requested.
- Response payload: {tasks: [{groupTask, patient, childTasks[], serviceRequest?}], totalCount, offset, limit} ready for rendering.
- Pagination: "Next" button increments offset; "Previous" decrements; buttons disabled if no more results.
- Details action renders ServiceRequest info (code, priority, status, notes) and child task summary.
- Bulk update: select status from allowed transitions only -> POST /api/task-groups/{groupId}/status?newStatus=<status> -> on success, refresh task list and open panel; on invalid transition, warn with message and do not submit.

Status Options & Transitions
- Allowed statuses: draft, requested, accepted, in-progress, completed, failed, cancelled.
- State machine (enforce on bulk update):
  - requested -> accepted, cancelled (only these transitions)
  - accepted -> in-progress, completed, failed, cancelled
  - in-progress -> completed, failed, cancelled
  - draft -> requested, cancelled
  - Terminals (no further transitions): completed, failed, cancelled
- On invalid transition, POST returns 400 with message; UI shows warning toast and does not update.

Testing
- API returns organisations discovered from Task owners with fulfilment-task-group tag.
- API returns paginated tasks for selected org; offset/limit controls work correctly; tasks at boundary pages render right count.
- Bulk update validates state transition; rejects invalid transitions with 400; succeeds on valid transitions and updates child tasks.
- UI renders org dropdown, task table with pagination, details panel; pagination controls enable/disable correctly; transition warnings show for invalid attempts.


