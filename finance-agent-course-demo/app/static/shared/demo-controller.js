(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  class DemoController {
    constructor(options) {
      this.totalSteps = options.totalSteps;
      this.delays = options.delays || [];
      this.onStep = options.onStep || function () {};
      this.onReset = options.onReset || function () {};
      this.current = options.startStep || 1;
      this.timer = null;
      this.playing = false;
      this.bind();
      this.render();
      this.onStep(this.current, this);
    }

    bind() {
      var self = this;
      var actions = {
        "btn-prev": function () { self.previous(); },
        "btn-next": function () { self.next(); },
        "btn-auto": function () { self.startAuto(); },
        "btn-pause": function () { self.pause(); },
        "btn-continue": function () { self.continueAuto(); },
        "btn-reset": function () { self.reset(); },
        "btn-final": function () { self.jumpEnd(); }
      };
      Object.keys(actions).forEach(function (id) {
        var element = byId(id);
        if (element) element.addEventListener("click", actions[id]);
      });
      var select = byId("step-select");
      if (select) select.addEventListener("change", function () { self.goTo(Number(select.value)); });
      document.querySelectorAll("[data-step-jump]").forEach(function (element) {
        element.addEventListener("click", function () { self.goTo(Number(element.dataset.stepJump)); });
      });
    }

    render() {
      var percent = this.totalSteps <= 1 ? 100 : ((this.current - 1) / (this.totalSteps - 1)) * 100;
      var progress = byId("progress-fill");
      if (progress) progress.style.width = percent + "%";
      var count = byId("step-count");
      if (count) count.textContent = "第 " + this.current + " / " + this.totalSteps + " 步";
      var select = byId("step-select");
      if (select) select.value = String(this.current);
      var prev = byId("btn-prev");
      var next = byId("btn-next");
      var auto = byId("btn-auto");
      var pause = byId("btn-pause");
      var cont = byId("btn-continue");
      var final = byId("btn-final");
      if (prev) prev.disabled = this.current <= 1;
      if (next) next.disabled = this.current >= this.totalSteps;
      if (auto) auto.disabled = this.playing || this.current >= this.totalSteps;
      if (pause) pause.disabled = !this.playing;
      if (cont) cont.disabled = this.playing || this.current >= this.totalSteps;
      if (final) final.disabled = this.current >= this.totalSteps;
      document.querySelectorAll("[data-step-dot]").forEach(function (dot) {
        var step = Number(dot.dataset.stepDot);
        dot.classList.toggle("active", step === this.current);
        dot.classList.toggle("done", step < this.current);
      }, this);
    }

    goTo(step) {
      var target = Math.max(1, Math.min(this.totalSteps, step));
      this.stopTimer();
      this.current = target;
      this.playing = false;
      this.render();
      this.onStep(this.current, this);
    }

    next() {
      if (this.current < this.totalSteps) this.goTo(this.current + 1);
    }

    previous() {
      if (this.current > 1) this.goTo(this.current - 1);
    }

    startAuto() {
      if (this.current >= this.totalSteps) return;
      this.playing = true;
      this.render();
      this.schedule();
    }

    schedule() {
      var self = this;
      this.stopTimer();
      var delay = this.delays[this.current - 1] || 1200;
      this.timer = window.setTimeout(function () {
        if (!self.playing) return;
        if (self.current < self.totalSteps) {
          self.current += 1;
          self.render();
          self.onStep(self.current, self);
          if (self.current < self.totalSteps) self.schedule();
          else self.playing = false;
          self.render();
        }
      }, delay);
    }

    pause() {
      if (!this.playing) return;
      this.playing = false;
      this.stopTimer();
      this.render();
    }

    continueAuto() {
      if (this.current >= this.totalSteps) return;
      this.playing = true;
      this.render();
      this.schedule();
    }

    jumpEnd() {
      this.goTo(this.totalSteps);
    }

    reset() {
      this.stopTimer();
      this.playing = false;
      this.current = 1;
      this.onReset(this);
      this.render();
      this.onStep(this.current, this);
    }

    stopTimer() {
      if (this.timer !== null) {
        window.clearTimeout(this.timer);
        this.timer = null;
      }
    }
  }

  window.DemoController = DemoController;
  window.enableFullscreen = function () {
    var target = document.documentElement;
    if (document.fullscreenElement) {
      if (document.exitFullscreen) document.exitFullscreen();
      return;
    }
    if (target.requestFullscreen) {
      target.requestFullscreen().catch(function () {});
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-fullscreen]").forEach(function (button) {
      button.addEventListener("click", window.enableFullscreen);
    });
  });
}());

