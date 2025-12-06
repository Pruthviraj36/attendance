function showToast(title, message, type = 'info') {
    const notif = document.getElementById('custom-notification');
    const toastTitle = document.getElementById('notif-title');
    const toastMessage = document.getElementById('notif-message');
    const toastCard = notif.firstElementChild;

    toastTitle.textContent = title;
    toastMessage.textContent = message;

    // Reset colors
    toastCard.className = 'glass-card bg-opacity-90 backdrop-blur-md border border-white/20 p-4 rounded-xl shadow-2xl flex items-center gap-3 min-w-[300px] transition-colors duration-300';

    if (type === 'success') {
        toastCard.classList.add('bg-emerald-600/90');
    } else if (type === 'danger') {
        toastCard.classList.add('bg-red-600/90');
    } else {
        toastCard.classList.add('bg-blue-600/90');
    }

    notif.classList.remove('translate-x-full', 'opacity-0');
    setTimeout(() => hideNotification(), 3000);
}

function hideNotification() {
    const notif = document.getElementById('custom-notification');
    if (notif) {
        notif.classList.add('translate-x-full', 'opacity-0');
    }
}

// Accept defaultSlot as argument
function attendanceApp(defaultSlot = 'default') {
    return {
        // State: Use the passed argument, NOT Jinja syntax
        selectedSlot: defaultSlot,
        students: {},
        studentIds: [],
        currentIndex: 0,
        totalStudents: 0,

        isLoading: false,
        hasError: false,
        showFilters: true,
        isTransitioning: false,

        // Filter Models
        startRoll: '',
        endRoll: '',
        selectedBatch: '',

        get currentStudentEnrollment() {
            return this.studentIds[this.currentIndex];
        },

        get presentCount() { return Object.values(this.students).filter(s => s === 'P').length; },
        get absentCount() { return Object.values(this.students).filter(s => s === 'A').length; },

        get isValidRollRange() {
            const start = parseInt(this.startRoll);
            const end = parseInt(this.endRoll);
            if (!this.startRoll && !this.endRoll) return true;
            return !isNaN(start) && !isNaN(end) && start < end;
        },

        // Lifecycle
        init() {
            this.initKeyboard();
            window.addEventListener('students-loaded', (e) => {
                console.log("Event received: students-loaded", e.detail);
                this.initStudentsList(e.detail);
                this.showFilters = false;
            });
        },

        // Navigation
        nextStudent() {
            if (this.currentIndex < this.totalStudents - 1) {
                this.currentIndex++;
            }
        },

        prevStudent() {
            if (this.currentIndex > 0) {
                this.currentIndex--;
            }
        },

        markCurrent(status) {
            if (this.isTransitioning) return;

            const enroll = this.currentStudentEnrollment;
            if (enroll) {
                this.students[enroll] = status;

                if (this.currentIndex < this.totalStudents - 1) {
                    this.isTransitioning = true;
                    setTimeout(() => {
                        this.nextStudent();
                        setTimeout(() => {
                            this.isTransitioning = false;
                        }, 350);
                    }, 50);
                } else if (this.currentIndex === this.totalStudents - 1) {
                    showToast('Done', 'You reached the end of the list!', 'success');
                }
            }
        },

        initStudentsList(ids) {
            this.studentIds = ids;
            this.totalStudents = ids.length;
            this.currentIndex = 0;
            ids.forEach(id => {
                if (this.students[id] === undefined) this.students[id] = null;
            });
        },

        initKeyboard() {
            document.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT') return;

                switch (e.key) {
                    case 'ArrowRight':
                    case 'ArrowDown':
                        if (!this.isTransitioning) this.nextStudent();
                        break;
                    case 'ArrowLeft':
                    case 'ArrowUp':
                        if (!this.isTransitioning) this.prevStudent();
                        break;
                    case 'p':
                    case 'P':
                        this.markCurrent('P');
                        break;
                    case 'a':
                    case 'A':
                        this.markCurrent('A');
                        break;
                }
            });
        },

        async saveAttendance() {
            this.isLoading = true;

            const unmarked = this.studentIds.filter(id => !this.students[id]);
            if (unmarked.length > 0) {
                if (!confirm(`You have ${unmarked.length} unmarked students. Save anyway?`)) {
                    this.isLoading = false;
                    return;
                }
            }

            try {
                const payload = this.studentIds.map(id => ({
                    enrollment_no: id,
                    status: this.students[id]
                })).filter(s => s.status !== null);

                console.log('saveAttendance: studentIds=', this.studentIds);
                console.log('saveAttendance: students=', this.students);
                console.log('saveAttendance: payload=', payload);

                const res = await fetch('/save_attendance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        slot_name: this.selectedSlot,
                        students: payload
                    })
                });

                const data = await res.json();
                if (data.success) {
                    showToast('Success', 'Attendance Saved!', 'success');
                } else {
                    throw new Error(data.message || 'Unknown error');
                }
            } catch (e) {
                showToast('Error', e.message || 'Error saving attendance.', 'danger');
            } finally {
                this.isLoading = false;
            }
        },

        toggleAttendance(enrollment) { this.markCurrent(enrollment); },
        initStudent(enrollment) { }
    }
}