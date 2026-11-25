
document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("plannerForm");
    const taskInput = document.getElementById("task");
    const subjectInput = document.getElementById("subject");
    const dateInput = document.getElementById("studyDate");
    const durationInput = document.getElementById("duration");
    const planList = document.getElementById("planList");
    const planCount = document.getElementById("planCount");

    async function loadPlans() {
        try {
            const response = await fetch("/api/plans");

            if (!response.ok) {
                throw new Error("Could not load plans.");
            }

            const plans = await response.json();
            renderPlans(plans);

        } catch (error) {
            planList.textContent = "Unable to load study plans. Please refresh.";
        }
    }

    function renderPlans(plans) {

        planList.innerHTML = "";

        planCount.textContent =
            plans.length + (plans.length === 1 ? " plan" : " plans");

        if (plans.length === 0) {
            planList.innerHTML =
                '<p class="empty-message">No study plans yet. Create your first plan!</p>';
            return;
        }

        plans.forEach(function (plan) {

            const card = document.createElement("div");
            card.className = "planner-card";

            const title = document.createElement("h3");
            title.textContent = plan.task;

            const details = document.createElement("p");
            details.textContent =
                plan.subject + " • " + plan.date + " • " + plan.duration;

            const status = document.createElement("p");
            status.textContent = plan.completed ? "Completed ✓" : "Pending";

            const completeButton = document.createElement("button");
            completeButton.textContent =
                plan.completed ? "Completed ✓" : "Mark Complete";
            completeButton.className = "add-button";
            completeButton.disabled = plan.completed;

            completeButton.addEventListener("click", async function () {
                try {
                    const response = await fetch("/api/plans/" + plan.id, {
                        method: "PATCH",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ completed: true })
                    });

                    if (!response.ok) {
                        throw new Error("Update failed.");
                    }

                    loadPlans();

                } catch (error) {
                    alert("Unable to update study plan.");
                }
            });

            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Delete";
            deleteButton.className = "delete-button";

            deleteButton.addEventListener("click", async function () {

                if (!confirm("Delete this study plan?")) {
                    return;
                }

                try {
                    const response = await fetch("/api/plans/" + plan.id, {
                        method: "DELETE"
                    });

                    if (!response.ok) {
                        throw new Error("Delete failed.");
                    }

                    loadPlans();

                } catch (error) {
                    alert("Unable to delete study plan.");
                }
            });

            card.appendChild(title);
            card.appendChild(details);
            card.appendChild(status);
            card.appendChild(completeButton);
            card.appendChild(deleteButton);

            planList.appendChild(card);
        });
    }

    form.addEventListener("submit", async function (event) {

        event.preventDefault();

        const newPlan = {
            task: taskInput.value.trim(),
            subject: subjectInput.value.trim(),
            date: dateInput.value,
            duration: durationInput.value
        };

        if (!newPlan.task || !newPlan.subject ||
            !newPlan.date || !newPlan.duration) {
            alert("Please fill all fields.");
            return;
        }

        try {
            const response = await fetch("/api/plans", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(newPlan)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || "Could not add plan.");
            }

            form.reset();
            alert("Study plan added successfully!");

            loadPlans();

        } catch (error) {
            alert(error.message || "Unable to save study plan.");
        }
    });

    loadPlans();

});
