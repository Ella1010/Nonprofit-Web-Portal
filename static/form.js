document.addEventListener('DOMContentLoaded', function () {
  // ====== Multi-step Form Navigation ======
  const steps = Array.from(document.querySelectorAll('.form-step'));
  const progressSteps = document.querySelectorAll('.progress-step');
  const nextBtns = document.querySelectorAll('.next-btn');
  const prevBtns = document.querySelectorAll('.prev-btn');
  let current = 0


function autosaveFormData() {
  const form = document.getElementById('application-form');
  const formData = new FormData(form);
  const statusBox = document.getElementById('autosave-status');

  statusBox.textContent = "Saving...";

  fetch('/autosave', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      const now = new Date();
      const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      statusBox.textContent = `Last saved at ${timeString}`;
      setTimeout(() => { statusBox.textContent = ""; }, 5000);
    } else {
      statusBox.textContent = "Unable to save draft.";
      setTimeout(() => { statusBox.textContent = ""; }, 5000);
    }
  })
  .catch(() => {
    statusBox.textContent = "Network error. Changes may not be saved.";
    setTimeout(() => { statusBox.textContent = ""; }, 5000);
  });
}

/*let autosaveTimeout;
document.querySelectorAll('input, textarea, select').forEach(el => {
  el.addEventListener('input', () => {
    clearTimeout(autosaveTimeout);
    autosaveTimeout = setTimeout(autosaveFormData, 2000);
  });
});*/



  function showStep(index) {
    steps.forEach((step, i) => {
      step.classList.toggle('active', i === index);
      progressSteps[i].classList.toggle('active', i <= index);
    });
  }


function generateReviewContent() {
  const form = document.getElementById('application-form');
  const formData = new FormData(form);
  const data = {};
  for (const [key, value] of formData.entries()) {
    data[key] = value;
  }

  const block = (title, entries) => {
    let html = `<h4 style="margin-top: 1.5em;">${title}</h4>`;
    entries.forEach(([label, key]) => {
      const val = data[key];
      if (val) html += `<div><strong>${label}:</strong> ${val}</div>`;
    });
    return html;
  };

  const sections = [
    block("Student Info", [
      ["Student Name", "student_name"],
      ["Gender", "student_gender"],
      ["Gender (Other)", "student_gender_other"],
      ["Date of Birth", "dob"],
      ["Email", "email"],
      ["Phone", "phone"],
      ["Grade", "grade"],
    ]),
    block("Parent Info", [
      ["Parent Name", "parent_name"],
      ["Parent Contact", "parent_contact"],
    ]),
    block("School Info", [
      ["School Name", "school_name"],
      ["School Location", "school_location"],
      ["School Contact", "school_contact"],
    ]),
    block("Teacher Info", [
      ["Teacher Name", "teacher_name"],
      ["Teacher Contact", "teacher_contact"],
      ["Teacher Email", "teacher_email"],
    ]),
    block("Essays", [
      ["Essay 1", "essay1"],
      ["Essay 2", "essay2"],
      ["Essay 3", "essay3"],
      ["Optional Info", "optional_info"],
    ])
  ];

  // Render basic blocks
  document.getElementById('review-content').innerHTML = sections.join("\n");

  // ✅ ADD THIS — render activities block
  const activityTypes = formData.getAll("activity_type[]");
  const positions = formData.getAll("activity_position[]");
  const orgs = formData.getAll("activity_org[]");
  const descs = formData.getAll("activity_desc[]");

  if (activityTypes.length > 0) {
    let html = `<h4 style="margin-top: 1.5em;">Activities</h4>`;
    for (let i = 0; i < activityTypes.length; i++) {
      const type = activityTypes[i] || '';
      const pos = positions[i] || '';
      const org = orgs[i] || '';
      const desc = descs[i] || '';
      html += `<div style="margin-bottom: 1em;">
        <strong>Activity ${i + 1}</strong><br>
        <strong>Type:</strong> ${type}<br>
        <strong>Position:</strong> ${pos}<br>
        <strong>Organization:</strong> ${org}<br>
        <strong>Description:</strong> ${desc}
      </div>`;
    }
    document.getElementById('review-content').innerHTML += html;
  }
}






nextBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    console.log("next clicked");  // debug
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


function createActivityBlock(type = '', position = '', org = '', desc = '') {
  const div = document.createElement('div');
  div.className = 'activity-block';
  div.innerHTML = `
    <hr />
    <h3>Activity</h3>
    <label>Activity Name<input name="activity_type[]" value="${type}" required /></label>
    <label>Position<input name="activity_position[]" value="${position}" maxlength="50" required /></label>
    <label>Organization<input name="activity_org[]" value="${org}" maxlength="100" required /></label>
    <label>Description<textarea name="activity_desc[]" required>${desc}</textarea></label>
    <button type="button" class="remove-activity">❌ Remove</button>
  `;

  const removeBtn = div.querySelector('.remove-activity');
  removeBtn.addEventListener('click', () => div.remove());
  



  const descTextarea = div.querySelector('textarea[name="activity_desc[]"]');
  enforceWordLimit(descTextarea, 50);

  div.querySelectorAll('input, textarea, select').forEach(el => {
  el.addEventListener('input', () => {
    clearTimeout(autosaveTimeout);
    autosaveTimeout = setTimeout(autosaveFormData, 2000);
  });
});


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
if (window.prefilledActivities && window.prefilledActivities.length) {
  container.innerHTML = '';  // clear first auto-added block
  window.prefilledActivities.forEach(act => {
    container.appendChild(createActivityBlock(
      act.activity_type,
      act.activity_position,
      act.activity_org,
      act.activity_desc
    ));
  });
}



  // ====== Final Validation Before Submit ======






document.getElementById('application-form').addEventListener('submit', function (e) {

   let formValid = true;

  // Clear old highlights
  document.querySelectorAll('.highlight-missing').forEach(el => {
    el.classList.remove('highlight-missing');
  });

  // Check all required fields
  document.querySelectorAll('#application-form [required]').forEach(input => {
    if (!input.value || input.value.trim() === '') {
      formValid = false;
      input.classList.add('highlight-missing');
    }
  });

  if (!formValid) {
    e.preventDefault();
    alert('Please complete all required fields highlighted in red.');
    return;
  }

  const gradeReportInput = document.querySelector('input[name="grade_report"]');
if (!gradeReportInput.files || gradeReportInput.files.length === 0) {
  e.preventDefault();
  alert("Please upload your most recent grade report.");
  return;
}
  if (current !== steps.length - 1) {
    e.preventDefault();  // prevent accidental submit on intermediate steps
    return;
  }




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

  // SCROLL TO FIRST INVALID FIELD
  const firstInvalid = this.querySelector(':invalid');
  if (firstInvalid) {
    firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
    firstInvalid.focus();
    e.preventDefault();  // prevent submission
    alert("Please fill out all required fields.");
    return;
  }

    if (tooLong) {
      e.preventDefault();
      alert("Please fix fields that exceed word limits before submitting.");
    }
  });

// ✅ Attach autosave listeners to ALL current form fields (including optional_info)
setTimeout(() => {
  document.querySelectorAll('input, textarea, select').forEach(el => {
    el.addEventListener('input', () => {
      clearTimeout(autosaveTimeout);
      autosaveTimeout = setTimeout(autosaveFormData, 2000);
    });
    console.log("Autosave attached to:", el.name); // optional debug
  });
}, 50);


});
