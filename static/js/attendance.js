function showToast(title, message, type = 'info') {
    const notif = document.getElementById('custom-notification');
    document.getElementById('notif-title').textContent = title;
    document.getElementById('notif-message').textContent = message;
    notif.classList.remove('bg-green-500', 'bg-red-500', 'bg-blue-500');
    if (type === 'success') notif.classList.add('bg-green-500');
    else if (type === 'danger') notif.classList.add('bg-red-500');
    else notif.classList.add('bg-blue-500');
    notif.classList.remove('hidden');
    setTimeout(() => notif.classList.add('hidden'), 5000);
}

function hideNotification() {
    document.getElementById('custom-notification').classList.add('hidden');
}

function attendanceApp() {
    return {
        selectedSlot: '{{ slots[0].name if slots else "default" }}',
        students: {},
        isLoading: false,
        hasError: false,
        startRoll: '',
        endRoll: '',
        selectedBatch: '',
        selectedSemester: '',
        currentPage: 1,

        get presentCount() { return Object.values(this.students).filter(s => s === 'P').length; },
        get absentCount() { return Object.values(this.students).filter(s => s === 'A').length; },

        get isValidRollRange() {
            const start = parseInt(this.startRoll);
            const end = parseInt(this.endRoll);
            return this.startRoll && this.endRoll && !isNaN(start) && !isNaN(end) && start > 0 && end > 0 && start < end;
        },

        toggleAttendance(enrollment) {
            this.students[enrollment] = this.students[enrollment] === 'P' ? 'A' : 'P';
        },

        initStudent(enrollment) {
            if (!this.students[enrollment]) this.students[enrollment] = 'P';
        },

        async saveAttendance() {
            this.isLoading = true;
            this.hasError = false;
            try {
                const res = await fetch('/save_attendance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        slot_name: this.selectedSlot,
                        students: Object.entries(this.students).map(([k, v]) => ({ enrollment_no: k, status: v }))
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Success', 'Attendance Saved & Uploading!', 'success');
                    setTimeout(() => document.getElementById('save-attendance-btn').focus(), 1000);
                } else {
                    throw new Error(data.message || 'Unknown error');
                }
            } catch (e) {
                this.hasError = true;
                showToast('Error', 'Error saving attendance. Please try again.', 'danger');
                setTimeout(() => document.getElementById('save-attendance-btn').focus(), 1000);
            } finally {
                this.isLoading = false;
            }
        },

        retrySave() {
            this.saveAttendance();
        },

        focusFirstStudent() {
            setTimeout(() => {
                const first = document.querySelector('#student-table tr:first-child');
                if (first) first.focus();
            }, 100);
        },

        prevPage() {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadStudents();
            }
        },

        nextPage() {
            this.currentPage++;
            this.loadStudents();
        },

        loadStudents() {
            htmx.trigger('#load-students-btn', 'click');
        }
    }
}