(function () {
  "use strict";

  window.initInstructorGuide = function () {
    var guide = document.getElementById("instructor-guide");
    var toggle = document.getElementById("btn-guide");
    if (!guide || !toggle) return;
    var key = "finance-demo.instructor-guide";
    var visible = true;
    try {
      visible = window.sessionStorage.getItem(key) !== "0";
    } catch (error) {}

    function apply() {
      guide.hidden = !visible;
      toggle.textContent = visible ? "隐藏讲师说明" : "显示讲师说明";
      toggle.setAttribute("aria-expanded", visible ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      visible = !visible;
      try { window.sessionStorage.setItem(key, visible ? "1" : "0"); } catch (error) {}
      apply();
    });
    apply();
  };
}());

