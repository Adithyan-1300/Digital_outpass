// Staff/Advisor Module JavaScript

// Load staff dashboard
async function loadStaffDashboard() {
    try {
        const response = await fetch(`${app.API_BASE}/staff/dashboard-stats`);
        const data = await response.json();

        if (data.success) {
            const stats = data.stats;
            document.getElementById('moduleContent').innerHTML = `
                <div style="margin-bottom: 32px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h2 style="font-size: 32px; font-weight: 700;">Staff Dashboard</h2>
                        <p style="color: var(--text-muted);">Manage your student's outpass requests and approvals.</p>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="modern-card">
                        <div class="stat-icon" style="background: rgba(245, 158, 11, 0.1); color: var(--warning);"><i class="ph ph-bell-ringing"></i></div>
                        <div>
                            <div class="stat-value">${stats.pending_requests || 0}</div>
                            <div class="stat-label">Pending Requests</div>
                        </div>
                    </div>
                    <div class="modern-card">
                        <div class="stat-icon"><i class="ph ph-users-three"></i></div>
                        <div>
                            <div class="stat-value">${stats.total_students || 0}</div>
                            <div class="stat-label">My Students</div>
                        </div>
                    </div>
                    <div class="modern-card">
                        <div class="stat-icon" style="background: rgba(16, 185, 129, 0.1); color: var(--success);"><i class="ph ph-calendar-check"></i></div>
                        <div>
                            <div class="stat-value">${stats.processed_this_month || 0}</div>
                            <div class="stat-label">Processed (Month)</div>
                        </div>
                    </div>
                </div>
                
                <div class="glass-panel" style="background: white; padding: 32px; border: none;">
                    <div style="margin-bottom: 24px;">
                        <h3 style="font-size: 20px; font-weight: 600;">Action Center</h3>
                        <p style="color: var(--text-muted); font-size: 14px;">Quick access to management tools.</p>
                    </div>
                    <div style="display: flex; gap: 16px;">
                        <button onclick="loadModule('pending-requests')" class="btn-modern btn-modern-primary" style="display: flex; align-items: center; gap: 8px;">
                            <i class="ph ph-timer"></i> View Pending Requests
                        </button>
                        <button onclick="loadModule('my-students')" class="btn-modern" style="background: #f1f5f9; color: var(--text-main); display: flex; align-items: center; gap: 8px;">
                            <i class="ph ph-users-four"></i> My Students
                        </button>
                    </div>
                </div>
            `;
        } else {
            document.getElementById('moduleContent').innerHTML = `<div class="card"><p>${data.message || 'Error loading dashboard'}</p></div>`;
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        document.getElementById('moduleContent').innerHTML = '<div class="card"><p>Error loading dashboard</p></div>';
    }
}

// Load pending requests
async function loadPendingRequests() {
    try {
        const response = await fetch(`${app.API_BASE}/staff/pending-requests`);
        const data = await response.json();

        if (data.success) {
            let html = `
                <div style="margin-bottom: 32px; display: flex; justify-content: space-between; align-items: center;">
                    <h2 style="font-size: 28px; font-weight: 700;">Pending Requests</h2>
                    <button onclick="loadModule('staff-dashboard')" class="btn-modern" style="background: #f1f5f9; color: var(--text-main); font-size: 14px;">
                        <i class="ph ph-arrow-left"></i> Back
                    </button>
                </div>
                
                <div class="table-wrapper">
                    <table class="modern-table">
                        <thead>
                            <tr>
                                <th>Student</th>
                                <th>Reg No</th>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Reason</th>
                                <th style="text-align: right;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            if (data.requests.length === 0) {
                html += `<tr><td colspan="7" style="text-align: center; padding: 20px;">No pending requests.</td></tr>`;
            } else {
                data.requests.forEach(req => {
                    html += `
                        <tr>
                            <td style="font-weight: 600;">${req.student_name}</td>
                            <td>${req.registration_no}</td>
                            <td>${app.formatDate(req.out_date)}</td>
                            <td>${app.formatTime(req.out_time)}</td>
                            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${req.reason}</td>
                            <td>
                                <div style="display: flex; justify-content: flex-end;">
                                    <button onclick="reviewRequest(${req.outpass_id})" class="btn-modern btn-modern-primary" style="padding: 6px 16px; font-size: 13px;">Review</button>
                                </div>
                            </td>
                        </tr>
                    `;
                });
            }

            html += `</tbody></table></div>`;
            document.getElementById('moduleContent').innerHTML = html;
        } else {
            document.getElementById('moduleContent').innerHTML = `<div class="card"><p>${data.message || 'Error loading pending requests'}</p></div>`;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

// Review request
async function reviewRequest(outpassId) {
    try {
        const response = await fetch(`${app.API_BASE}/staff/pending-requests`);
        const data = await response.json();
        const op = data.requests.find(r => r.outpass_id === outpassId);

        if (op) {
            document.getElementById('moduleContent').innerHTML = `
                <div class="card" style="max-width: 600px; margin: 0 auto;">
                    <div style="display: flex; gap: 24px; align-items: start; margin-bottom: 24px;">
                        <div style="width: 120px; height: 120px; border-radius: 12px; background: #f1f5f9; overflow: hidden; display: flex; align-items: center; justify-content: center; border: 1px solid #e2e8f0;">
                            ${op.profile_image ? `<img src="${op.profile_image}" style="width: 100%; height: 100%; object-fit: cover;">` : '<i class="ph ph-user" style="font-size: 48px; color: #cbd5e1;"></i>'}
                        </div>
                        <div style="flex: 1;">
                            <h2 style="margin-bottom: 8px;">Review Request</h2>
                            <p style="font-size: 18px; font-weight: 600; color: var(--primary); margin-bottom: 4px;">${op.student_name}</p>
                             <p style="font-size: 14px; color: var(--text-muted); display: flex; align-items: center; gap: 4px;">
                                <i class="ph ph-users"></i> Parent: <span style="font-weight: 500; color: var(--text-main);">${op.parent_name || 'N/A'}</span>
                                ${op.parent_mobile ? `<span style="margin-left: 8px; font-weight: 500; color: var(--primary);"><i class="ph ph-phone"></i> ${op.parent_mobile}</span>` : ''}
                            </p>
                            <p style="font-size: 14px; color: var(--text-muted); margin-top: 4px;">${op.registration_no} | ${op.dept_name}</p>
                        </div>
                    </div>
                    
                    <div style="background: #f8fafc; padding: 20px; border-radius: 12px; margin-bottom: 24px;">
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
                            <div>
                                <p style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 4px;">Out Date</p>
                                <p style="font-weight: 600;">${app.formatDate(op.out_date)}</p>
                            </div>
                            <div>
                                <p style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); margin-bottom: 4px;">Reason</p>
                                <p style="font-weight: 600;">${op.reason}</p>
                            </div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Advisor Remarks</label>
                        <textarea id="remarks" rows="3" placeholder="Enter optional remarks..."></textarea>
                    </div>
                    <div style="display: flex; gap: 12px; margin-top: 8px;">
                        <button onclick="approveStaffRequest(${outpassId})" class="btn-modern btn-modern-primary" style="flex: 1;">Approve</button>
                        <button onclick="rejectStaffRequest(${outpassId})" class="btn-modern" style="flex: 1; background: #fee2e2; color: #991b1b;">Reject</button>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function approveStaffRequest(outpassId) {
    const remarks = document.getElementById('remarks').value || 'Approved';
    try {
        const response = await fetch(`${app.API_BASE}/staff/approve-request/${outpassId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ remarks })
        });
        const data = await response.json();
        alert(data.message);
        loadModule('pending-requests');
    } catch (error) {
        alert('Error approving request');
    }
}

async function rejectStaffRequest(outpassId) {
    const remarks = document.getElementById('remarks').value;
    if (!remarks) {
        alert('Please provide remarks');
        return;
    }
    try {
        const response = await fetch(`${app.API_BASE}/staff/reject-request/${outpassId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ remarks })
        });
        const data = await response.json();
        alert(data.message);
        loadModule('pending-requests');
    } catch (error) {
        alert('Error rejecting request');
    }
}

async function loadMyStudents() {
    try {
        const response = await fetch(`${app.API_BASE}/staff/my-students`);
        const data = await response.json();

        if (data.success) {
            let html = `
                <div class="card">
                    <h2>My Students</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Reg No</th>
                                <th>Email</th>
                                <th>Total Outpasses</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            data.students.forEach(s => {
                html += `
                    <tr>
                        <td>${s.full_name}</td>
                        <td>${s.registration_no}</td>
                        <td>${s.email}</td>
                        <td>${s.total_outpasses || 0}</td>
                        <td><button onclick="viewStudentHistory(${s.user_id})" class="btn btn-sm btn-primary">History</button></td>
                    </tr>
                `;
            });

            html += `</tbody></table></div>`;
            document.getElementById('moduleContent').innerHTML = html;
        } else {
            document.getElementById('moduleContent').innerHTML = `<div class="card"><p>${data.message || 'Error loading students'}</p></div>`;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}

async function viewStudentHistory(studentId) {
    try {
        const response = await fetch(`${app.API_BASE}/staff/student-history/${studentId}`);
        const data = await response.json();

        if (data.success) {
            let html = `<div class="card"><h2>${data.student.full_name} - History</h2><table>
                <thead><tr><th>Date</th><th>Reason</th><th>Status</th></tr></thead><tbody>`;

            data.history.forEach(h => {
                html += `<tr><td>${app.formatDate(h.out_date)}</td><td>${h.reason}</td><td>${app.getStatusBadge(h.final_status)}</td></tr>`;
            });

            html += `</tbody></table></div>`;
            document.getElementById('moduleContent').innerHTML = html;
        }
    } catch (error) {
        console.error('Error:', error);
    }
}