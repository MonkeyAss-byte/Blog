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
  const cards = document.querySelectorAll(
    ".center, .sidebar .explorer, .sidebar .recent-notes, .sidebar .toc, .sidebar .backlinks, .popover"
  ) as NodeListOf<HTMLElement>;
  
  const page = document.querySelector(".page") as HTMLElement;
  if (!page) return;

  // Variables to track swipe
  let touchStartY = 0;
  let isScrolling = false;

  // Global listener to dismiss focus when tapping outside
  document.addEventListener("touchstart", (e) => {
    // If we click outside any card, remove focus from all
    const target = e.target as Node;
    let clickedInsideCard = false;
    cards.forEach(card => {
      if (card.contains(target)) clickedInsideCard = true;
    });

    if (!clickedInsideCard) {
      cards.forEach(c => c.classList.remove("mobile-focused"));
      page.classList.remove("has-mobile-focus");
    }
  }, { passive: true });

  for (const card of cards) {
    if (card.dataset.mobileFocusInit) continue;
    card.dataset.mobileFocusInit = "true";

    card.addEventListener("touchstart", (e: TouchEvent) => {
      touchStartY = e.touches[0].clientY;
      isScrolling = false;
    }, { passive: true });

    card.addEventListener("touchmove", (e: TouchEvent) => {
      const touchY = e.touches[0].clientY;
      if (Math.abs(touchY - touchStartY) > 20) { // Increased threshold to avoid fat-finger misfires
        isScrolling = true; // User is swiping/scrolling
      }
    }, { passive: true });

    card.addEventListener("touchend", (e: TouchEvent) => {
      if (isScrolling) return; // Filter out swipes

      // It's a clean tap!
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
        // Optional: scroll slightly to center it
        // card.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
  }
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

  const topDiv = document.createElement("div");
  topDiv.className = "edge-blur-layer";
  topDiv.style.top = "0";
  topDiv.style.height = "100px";
  topDiv.style.backdropFilter = "blur(12px)";
  topDiv.style.webkitBackdropFilter = "blur(12px)";
  topDiv.style.maskImage = "linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)";
  topDiv.style.webkitMaskImage = "linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)";
  
  const bottomDiv = document.createElement("div");
  bottomDiv.className = "edge-blur-layer";
  bottomDiv.style.bottom = "0";
  bottomDiv.style.height = "100px";
  bottomDiv.style.backdropFilter = "blur(12px)";
  bottomDiv.style.webkitBackdropFilter = "blur(12px)";
  bottomDiv.style.maskImage = "linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)";
  bottomDiv.style.webkitMaskImage = "linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)";
  
  document.body.appendChild(topDiv);
  document.body.appendChild(bottomDiv);
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

