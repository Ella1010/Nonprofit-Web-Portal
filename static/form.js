document.addEventListener('DOMContentLoaded', function () {
  // ====== Multi-step Form Navigation ======
  const steps = Array.from(document.querySelectorAll('.form-step'));
  const progressSteps = document.querySelectorAll('.progress-step');
  const nextBtns = document.querySelectorAll('.next-btn');
  const prevBtns = document.querySelectorAll('.prev-btn');
  let current = 0;

  function showStep(index) {
    steps.forEach((step, i) => {
      step.classList.toggle('active', i === index);
      progressSteps[i].classList.toggle('active', i <= index);
    });
  }

  function generateReviewContent() {
    const form = document.getElementById('application-form');
    const formData = new FormData(form);
    let review = '';

    const labelMap = {
  student_name: "Student Name",
  student_gender: "Gender",
  student_gender_other: "Gender (Other)",
  dob: "Date of Birth",
  email: "Email",
  phone: "Phone",
  grade: "Grade",
  parent_name: "Parent Name",
  parent_contact: "Parent Contact",
  school_name: "School Name",
  school_location: "School Location",
  school_contact: "School Contact",
  teacher_name: "Teacher Name",
  teacher_contact: "Teacher Contact",
  teacher_email: "Teacher Email",
  subjects: "Subjects",
  interests: "Academic Interests",
  essay1: "Essay 1",
  essay2: "Essay 2",
  essay3: "Essay 3",
  optional_info: "Optional Info",
  "activity_type[]": "Activity Type",
  "activity_position[]": "Activity Position",
  "activity_org[]": "Activity Organization",
  "activity_desc[]": "Activity Description"
};

for (const [key, value] of formData.entries()) {
  if (key === 'upload' || key === 'grade_report') continue;
  const label = labelMap[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  review += `${label}: ${value}\n\n`;
}


    document.getElementById('review-content').textContent = review;
  }

  nextBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (current < steps.length - 1) {
        current++;
        showStep(current);
        if (current === steps.length - 1) generateReviewContent();
      }
    });
  });

  prevBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      if (current > 0) {
        current--;
        showStep(current);
      }
    });
  });

  showStep(current);

  

  // ====== Word Limit Helper ======
  function enforceWordLimit(textarea, limit) {
    const counter = document.createElement('div');
    counter.style.fontSize = '12px';
    counter.style.marginTop = '4px';
    counter.style.color = '#555';
    textarea.parentNode.appendChild(counter);

    const warning = document.createElement('div');
    warning.style.color = 'red';
    warning.style.fontSize = '12px';
    warning.className = 'word-limit-warning';
    warning.style.display = 'none';
    warning.textContent = `⚠️ Max ${limit} words allowed. Please shorten your text.`;
    textarea.parentNode.appendChild(warning);

    function updateCounter() {
      const words = textarea.value.trim().split(/\s+/).filter(Boolean);
      counter.textContent = `Words: ${words.length} / ${limit}`;

      if (words.length > limit) {
        warning.style.display = 'block';
      } else {
        warning.style.display = 'none';
      }
    }

    textarea.addEventListener('input', updateCounter);
    updateCounter(); // initialize
  }

  // Apply word limits to essays
  enforceWordLimit(document.querySelector('textarea[name="essay1"]'), 150);
  enforceWordLimit(document.querySelector('textarea[name="essay2"]'), 200);
  enforceWordLimit(document.querySelector('textarea[name="essay3"]'), 150);

  // ====== Activity Block Add/Remove ======
  const addBtn = document.getElementById('add-activity');
  const container = document.getElementById('activities-container');

  function createActivityBlock() {
    const div = document.createElement('div');
    div.className = 'activity-block';
    div.innerHTML = `
      <hr />
      <h3>Activity</h3>
      <label>Activity Name<input name="activity_type[]" required /></label>
      <label>Position<input name="activity_position[]" maxlength="50" required /></label>
      <label>Organization<input name="activity_org[]" maxlength="100" required /></label>
      <label>Description<textarea name="activity_desc[]" required></textarea></label>
      <button type="button" class="remove-activity">❌ Remove</button>
    `;

    const removeBtn = div.querySelector('.remove-activity');
    removeBtn.addEventListener('click', () => div.remove());

    const descTextarea = div.querySelector('textarea[name="activity_desc[]"]');
    enforceWordLimit(descTextarea, 50);

    return div;
  }

  addBtn.addEventListener('click', () => {
    if (container.children.length < 5) {
      container.appendChild(createActivityBlock());
    } else {
      alert("You can only add up to 5 activities.");
    }
  });

  // Start with one activity block
  addBtn.click();

  // ====== Final Validation Before Submit ======
  document.getElementById('application-form').addEventListener('submit', function (e) {
    let tooLong = false;

    // Check activity descriptions
    const descs = document.querySelectorAll('textarea[name="activity_desc[]"]');
    descs.forEach(textarea => {
      const words = textarea.value.trim().split(/\s+/).filter(Boolean);
      const warning = textarea.parentNode.querySelector('.word-limit-warning');
      if (words.length > 50) {
        if (warning) warning.textContent = `⚠️ This activity description has ${words.length} words (limit: 50).`;
        tooLong = true;
      } else {
        if (warning) warning.textContent = '';
      }
    });

    // Check essays
    const essayLimits = {
      'essay1': 150,
      'essay2': 200,
      'essay3': 150
    };

    Object.entries(essayLimits).forEach(([name, limit]) => {
      const textarea = document.querySelector(`textarea[name="${name}"]`);
      const words = textarea.value.trim().split(/\s+/).filter(Boolean);
      const warning = textarea.parentNode.querySelector('.word-limit-warning');
      if (words.length > limit) {
        if (warning) warning.textContent = `⚠️ This essay has ${words.length} words (limit: ${limit}).`;
        tooLong = true;
      } else {
        if (warning) warning.textContent = '';
      }
    });

    if (tooLong) {
      e.preventDefault();
      alert("Please fix fields that exceed word limits before submitting.");
    }
  });
});
