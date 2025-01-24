// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
  // Initialize AOS
  AOS.init({
      duration: 1000,
      once: true
  });

  // Water drops animation
  function createWaterDrops() {
      const waterDrops = document.querySelector('.water-drops');
      if (waterDrops) {
          const drop = document.createElement('div');
          drop.classList.add('drop');
          drop.style.left = Math.random() * 100 + 'vw';
          drop.style.animationDuration = Math.random() * 2 + 3 + 's';
          waterDrops.appendChild(drop);
          setTimeout(() => drop.remove(), 5000);
      }
  }

  // Cart functionality
  function initializeCart() {
      const addToCartButtons = document.querySelectorAll('.add-to-cart');
      addToCartButtons.forEach(button => {
          button.addEventListener('click', function() {
              const productId = this.dataset.productId;
              addToCart(productId);
          });
      });
  }

  // Initialize all functions
  if (document.querySelector('.water-drops')) {
      setInterval(createWaterDrops, 300);
  }
  initializeCart();

    // Number counter animation
    const countElements = document.querySelectorAll('.stat-number');
    
    function animateCounter(element) {
        const target = parseInt(element.getAttribute('data-count'));
        const start = parseInt(element.textContent);
        const duration = 2000;
        const increment = (target - start) / (duration / 16);
        let current = start;

        const updateCounter = () => {
            current += increment;
            element.textContent = Math.floor(current).toLocaleString();

            if ((increment > 0 && current < target) || (increment < 0 && current > target)) {
                requestAnimationFrame(updateCounter);
            } else {
                element.textContent = target.toLocaleString();
            }
        };

        requestAnimationFrame(updateCounter);
    }

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateCounter(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    countElements.forEach(element => observer.observe(element));
});