// 1. Reveal Highlight Effect (Global Listener)
const handleMouseMove = (e: MouseEvent) => {
  const cards = document.querySelectorAll(
    ".center, .sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;
  
  for (const card of cards) {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    card.style.setProperty("--mouse-x", `${x}px`);
    card.style.setProperty("--mouse-y", `${y}px`);
  }
};

// Only add the document listener once
if (!window.hasOwnProperty("fluentMotionInit")) {
  document.addEventListener("mousemove", handleMouseMove);
  (window as any).fluentMotionInit = true;
}

const maxTilt = 4; // degrees

function setupFluentMotion() {
  // 2. Stagger Animations for List Items
  const listItems = document.querySelectorAll(
    ".explorer ul li, .recent-notes ul li, .toc ul li"
  ) as NodeListOf<HTMLElement>;
  
  listItems.forEach((li, index) => {
    // Limit max delay to avoid too long waits
    const delay = Math.min(index * 40, 600);
    li.classList.add("stagger-item");
    li.style.animationDelay = `${delay}ms`;
  });

  // 3. 3D Card Tilt Effect (Only for sidebars & popovers)
  const tiltCards = document.querySelectorAll(
    ".sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;

  for (const card of tiltCards) {
    if (card.dataset.fluentTiltInit) continue;
    card.dataset.fluentTiltInit = "true";

    card.addEventListener("mousemove", (e: MouseEvent) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const tiltX = ((y - centerY) / centerY) * -maxTilt;
      const tiltY = ((x - centerX) / centerX) * maxTilt;

      card.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(1.02, 1.02, 1.02)`;
      card.style.transition = "transform 0.1s ease";
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)`;
      card.style.transition = "transform 0.4s ease";
    });
  }
}

// --- 4. Mobile Tap-to-Focus Interaction ---
function setupMobileInteraction() {
  // Mobile click-to-expand has been explicitly disabled per user request.
  if (window.innerWidth <= 768) {
    return;
  }

  const cards = document.querySelectorAll(
    ".center, .sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;
  
  const page = document.querySelector(".page") as HTMLElement;
  if (!page) return;

  // We use 'click' instead of touch events because modern mobile browsers perfectly differentiate 
  // between a swipe/scroll and a true 'tap' (click), making this 100% reliable.
  for (const card of cards) {
    card.addEventListener("click", (e: Event) => {
      // Don't trigger if they clicked a link or button
      const target = e.target as HTMLElement;
      if (target.tagName.toLowerCase() === "a" || target.closest("a") || target.closest("button")) {
        return; 
      }

      const isAlreadyFocused = card.classList.contains("mobile-focused");
      
      // Remove focus from all cards first
      cards.forEach(c => c.classList.remove("mobile-focused"));

      if (isAlreadyFocused) {
        // Toggle off
        page.classList.remove("has-mobile-focus");
      } else {
        // Toggle on
        card.classList.add("mobile-focused");
        page.classList.add("has-mobile-focus");
      }
    });
  }

  // Clear focus when tapping outside any card
  document.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;
    if (!target.closest(".center") && !target.closest(".sidebar > *")) {
      cards.forEach(c => c.classList.remove("mobile-focused"));
      page.classList.remove("has-mobile-focus");
    }
  });
}

// --- 5. Dark Mode View Transition Hack ---
function setupDarkmodeTransition() {
  const btn = document.querySelector(".darkmode") as HTMLElement;
  if (!btn || btn.dataset.transitionInit) return;
  btn.dataset.transitionInit = "true";

  // Clone button to strip default Quartz listeners
  const clone = btn.cloneNode(true) as HTMLElement;
  btn.replaceWith(clone);

  clone.addEventListener("click", (e) => {
    const isDark = document.documentElement.getAttribute("saved-theme") === "dark";
    const newTheme = isDark ? "light" : "dark";

    const applyTheme = () => {
      document.documentElement.setAttribute("saved-theme", newTheme);
      localStorage.setItem("theme", newTheme);
      document.body.classList.remove("theme-dark", "theme-light");
      document.body.classList.add(`theme-${newTheme}`);
      document.dispatchEvent(new CustomEvent("themechange", { detail: { theme: newTheme } }));
    };

    if (!document.startViewTransition) {
      applyTheme();
      return;
    }

    const x = e.clientX;
    const y = e.clientY;
    const endRadius = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y));

    const transition = document.startViewTransition(() => applyTheme());
    // No explicit clip-path animation here, so it will fall back to a beautiful, soft cross-fade default!
  });
}

// --- 6. Smooth Viewport Edge Blur ---
// Uses a real DOM node with mask-image for a perfect gradient blur (distance field)
function setupEdgeBlur() {
  if (document.querySelector(".edge-blur-layer")) return; // Already setup
  
  // Only apply on desktop to avoid obscuring mobile UI
  if (window.innerWidth <= 768) return;

  const createSmoothBlur = (isTop: boolean) => {
    const div = document.createElement("div");
    div.className = `edge-blur-layer ${isTop ? "top" : "bottom"}`;
    div.style.position = "fixed";
    div.style[isTop ? "top" : "bottom"] = "0";
    div.style.left = "0";
    div.style.right = "0";
    div.style.height = "150px"; // Expanded range
    div.style.pointerEvents = "none";
    div.style.zIndex = "999999";
    
    // Stronger blur intensity
    div.style.backdropFilter = "blur(16px)";
    div.style.webkitBackdropFilter = "blur(16px)";
    
    // FADE THE BLUR ITSELF using a mask
    const direction = isTop ? "to bottom" : "to top";
    div.style.maskImage = `linear-gradient(${direction}, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)`;
    div.style.webkitMaskImage = `linear-gradient(${direction}, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)`;
    
    // FADE THE TEXT to the background color
    div.style.background = `linear-gradient(${direction}, var(--light) 20%, transparent 100%)`;
    
    return div;
  };

  document.body.appendChild(createSmoothBlur(true));
  document.body.appendChild(createSmoothBlur(false));
}

document.addEventListener("nav", () => {
  setupFluentMotion();
  setupMobileInteraction();
  setupDarkmodeTransition();
  setupEdgeBlur();
});
window.addEventListener("DOMContentLoaded", () => {
  setupFluentMotion();
  setupMobileInteraction();
  setupDarkmodeTransition();
  setupEdgeBlur();
});
// Run once immediately in case DOM is already loaded
setupFluentMotion();
setupMobileInteraction();
setupDarkmodeTransition();
setupEdgeBlur();

