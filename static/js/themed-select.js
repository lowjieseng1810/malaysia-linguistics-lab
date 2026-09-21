(function (root) {
  function closeAll(except) {
    document.querySelectorAll(".themed-select.is-open").forEach(function (widget) {
      if (widget === except) return;
      var menu = widget.querySelector(".themed-select-menu");
      var trigger = widget.querySelector(".themed-select-trigger");
      widget.classList.remove("is-open");
      if (menu) menu.hidden = true;
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  }

  function positionMenu(widget) {
    var trigger = widget.querySelector(".themed-select-trigger");
    var menu = widget.querySelector(".themed-select-menu");
    if (!trigger || !menu) return;
    var rect = trigger.getBoundingClientRect();
    var width = Math.max(rect.width, 220);
    menu.style.position = "fixed";
    menu.style.left = Math.max(8, rect.left) + "px";
    menu.style.width = width + "px";
    var below = rect.bottom + 6;
    menu.hidden = false;
    var menuHeight = menu.offsetHeight || 240;
    if (below + menuHeight > window.innerHeight - 8 && rect.top > menuHeight + 12) {
      menu.style.top = Math.max(8, rect.top - menuHeight - 6) + "px";
    } else {
      menu.style.top = below + "px";
    }
  }

  function rebuildOptions(widget) {
    var select = widget.querySelector("select");
    var menu = widget.querySelector(".themed-select-menu");
    var valueEl = widget.querySelector(".themed-select-value");
    if (!select || !menu || !valueEl) return;
    menu.innerHTML = "";
    Array.prototype.forEach.call(select.options, function (opt) {
      var li = document.createElement("li");
      li.setAttribute("role", "option");
      li.className = "themed-select-option";
      li.dataset.value = opt.value;
      li.textContent = opt.textContent;
      li.setAttribute("aria-selected", opt.selected ? "true" : "false");
      if (opt.disabled) li.setAttribute("aria-disabled", "true");
      menu.appendChild(li);
    });
    var selected = select.options[select.selectedIndex];
    valueEl.textContent = selected ? selected.textContent : "";
  }

  function bind(widget) {
    var trigger = widget.querySelector(".themed-select-trigger");
    var menu = widget.querySelector(".themed-select-menu");
    var select = widget.querySelector("select");
    var valueEl = widget.querySelector(".themed-select-value");
    if (!trigger || !menu || !select || !valueEl) return;

    function options() {
      return Array.prototype.slice.call(menu.querySelectorAll("[role='option']"));
    }

    function setFromOption(option, fireChange) {
      if (!option || option.getAttribute("aria-disabled") === "true") return;
      options().forEach(function (item) {
        item.setAttribute("aria-selected", item === option ? "true" : "false");
      });
      select.value = option.dataset.value;
      valueEl.textContent = option.textContent;
      closeAll();
      if (fireChange) {
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }

    trigger.addEventListener("click", function (ev) {
      ev.preventDefault();
      var open = widget.classList.contains("is-open");
      closeAll();
      if (!open) {
        rebuildOptions(widget);
        widget.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");
        positionMenu(widget);
      }
    });

    menu.addEventListener("click", function (ev) {
      var option = ev.target.closest("[role='option']");
      setFromOption(option, true);
    });

    trigger.addEventListener("keydown", function (ev) {
      var items = options();
      var current = items.findIndex(function (item) {
        return item.getAttribute("aria-selected") === "true";
      });
      if (ev.key === "ArrowDown" || ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        if (!widget.classList.contains("is-open")) {
          rebuildOptions(widget);
          widget.classList.add("is-open");
          trigger.setAttribute("aria-expanded", "true");
          positionMenu(widget);
          return;
        }
        var next = Math.min(items.length - 1, current + 1);
        if (items[next]) items[next].focus();
      } else if (ev.key === "ArrowUp") {
        ev.preventDefault();
        var prev = Math.max(0, current - 1);
        if (items[prev]) {
          if (!widget.classList.contains("is-open")) {
            rebuildOptions(widget);
            widget.classList.add("is-open");
            trigger.setAttribute("aria-expanded", "true");
            positionMenu(widget);
          }
          items[prev].focus();
        }
      } else if (ev.key === "Escape") {
        closeAll();
      }
    });

    menu.addEventListener("keydown", function (ev) {
      var items = options();
      var idx = items.indexOf(document.activeElement);
      if (ev.key === "ArrowDown") {
        ev.preventDefault();
        if (items[idx + 1]) items[idx + 1].focus();
      } else if (ev.key === "ArrowUp") {
        ev.preventDefault();
        if (items[idx - 1]) items[idx - 1].focus();
      } else if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        setFromOption(document.activeElement, true);
        trigger.focus();
      } else if (ev.key === "Escape") {
        ev.preventDefault();
        closeAll();
        trigger.focus();
      }
    });

    select.addEventListener("change", function () {
      rebuildOptions(widget);
    });
  }

  function enhance(select) {
    if (!select || select.dataset.themed === "1") return;
    select.dataset.themed = "1";
    select.classList.add("themed-select-native");
    var wrap = document.createElement("div");
    wrap.className = "themed-select";
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(select);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "themed-select-trigger";
    btn.setAttribute("aria-haspopup", "listbox");
    btn.setAttribute("aria-expanded", "false");
    var span = document.createElement("span");
    span.className = "themed-select-value";
    btn.appendChild(span);
    var menu = document.createElement("ul");
    menu.className = "themed-select-menu";
    menu.setAttribute("role", "listbox");
    menu.hidden = true;
    wrap.appendChild(btn);
    wrap.appendChild(menu);
    rebuildOptions(wrap);
    bind(wrap);
  }

  document.addEventListener("click", function (ev) {
    if (!ev.target.closest(".themed-select")) closeAll();
  });

  root.enhanceThemedSelect = enhance;
  root.rebuildThemedSelect = function (select) {
    var widget = select && select.closest(".themed-select");
    if (widget) rebuildOptions(widget);
  };
})(window);
