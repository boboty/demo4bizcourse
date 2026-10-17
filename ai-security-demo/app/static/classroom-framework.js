'use strict';
(() => {
  const controls = document.querySelector('.controls');
  let feedback = document.querySelector('.conclusion');
  const progress = document.getElementById('progress');
  const steps = [...document.querySelectorAll('.steps span')];
  const usesDoneProgress = !feedback;
  if (!controls || !progress || !steps.length) return;

  if (!feedback) {
    const result = document.getElementById('review-result');
    feedback = document.createElement('section');
    feedback.className = 'conclusion';
    feedback.setAttribute('aria-live', 'polite');
    const heading = document.createElement('h2');
    heading.textContent = '课堂结果反馈';
    feedback.append(heading);
    if (result) feedback.append(result);
  }
  feedback.classList.add('classroom-feedback');
  feedback.setAttribute('aria-label', '课堂结果反馈');
  controls.append(feedback);

  const next = document.createElement('span');
  next.className = 'classroom-next';
  next.setAttribute('aria-live', 'polite');
  progress.insertAdjacentElement('afterend', next);

  const actionButtons = [...controls.querySelectorAll('button')].filter(button =>
    !['reset', 'replay', 'boundary-check', 'export', 'download-brief'].includes(button.id)
  );
  const controlButtons = [...controls.querySelectorAll('button')];
  let forceInitial = false;
  const actionSteps = {
    identify: 0, assistant: 1, correct: 2, preview: 3, process: 3,
    normal: 0, pollute: 1, unsafe: 2, safe: 2,
    start: 0, analyze: 1, explain: 2, check: 3, review: 4, 'brief-button': 4
  };

  function paint() {
    const activeIndex = steps.reduce((last, step, index) => step.classList.contains('active') ? index : last, -1);
    const doneIndex = steps.reduce((last, step, index) => step.classList.contains('done') ? index : last, -1);
    const available = actionButtons.find(button => !button.disabled && button.dataset.classroomComplete !== 'true');
    const actionIndex = available && Object.hasOwn(actionSteps, available.id) ? actionSteps[available.id] : null;
    const inferredIndex = actionIndex ?? (usesDoneProgress ? doneIndex + 1 : activeIndex >= 0 ? activeIndex : 0);
    const currentIndex = forceInitial ? 0 : Math.min(steps.length - 1, Math.max(0, inferredIndex));
    steps.forEach((step, index) => {
      const current = index === currentIndex;
      const done = currentIndex >= 0 && index < currentIndex;
      step.classList.toggle('active', current);
      step.classList.toggle('done', done);
      step.setAttribute('data-status', current ? 'current' : done ? 'done' : 'upcoming');
      if (current) step.setAttribute('aria-current', 'step');
      else step.removeAttribute('aria-current');
    });

    const nextStep = steps[currentIndex + 1];
    next.textContent = nextStep ? `下一步：${nextStep.textContent.trim()}` : '下一步：课堂流程已完成，可重置后再次演示';

    controlButtons.forEach(button => {
      const primary = button === available;
      button.dataset.classroomPrimary = String(primary);
      button.dataset.classroomSecondary = String(!primary);
      if (primary) button.setAttribute('aria-label', `${button.textContent.trim()}（当前主操作）`);
      else button.removeAttribute('aria-label');
    });
  }

  function clearProgress() {
    actionButtons.forEach(item => { delete item.dataset.classroomComplete; });
    requestAnimationFrame(paint);
  }
  controls.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.id === 'replay') {
      forceInitial = false;
      clearProgress();
      return;
    }
    if (button.id !== 'replay' && actionButtons.includes(button)) {
      forceInitial = false;
      button.dataset.classroomComplete = 'true';
      requestAnimationFrame(paint);
    }
  });
  document.getElementById('reset')?.addEventListener('click', () => {
    forceInitial = true;
    clearProgress();
  });

  new MutationObserver(paint).observe(document.querySelector('.steps'), {attributes: true, subtree: true, attributeFilter: ['class']});
  new MutationObserver(paint).observe(controls, {attributes: true, subtree: true, attributeFilter: ['disabled']});
  paint();
})();
