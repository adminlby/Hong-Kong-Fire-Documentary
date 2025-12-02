/*
   Visitor Counter for MkDocs Material
   Integrates with the repository facts section (Stars/Forks) if possible.
*/

document.addEventListener("DOMContentLoaded", function() {
    initVisitorCounter();
});

function initVisitorCounter() {
    // 1. Inject Busuanzi Script if not already present
    if (!document.getElementById("busuanzi-script")) {
        var script = document.createElement("script");
        script.id = "busuanzi-script";
        script.src = "//busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js";
        script.async = true;
        document.body.appendChild(script);
    }

    // 2. Function to insert the counter
    function insertCounter() {
        // Check if we already have the counter
        if (document.getElementById("busuanzi_container_site_pv_custom")) {
            return;
        }

        // Strategy: Try to inject into .md-source__facts (where stars are)
        // If that fails (no repo configured or facts hidden), fallback to header

        var sourceRepository = document.querySelector(".md-source__repository");
        var headerInner = document.querySelector(".md-header__inner");

        if (sourceRepository) {
            // We have a repository block. Let's try to find or create the facts list.
            var facts = sourceRepository.querySelector(".md-source__facts");

            if (!facts) {
                // Facts list doesn't exist (yet? or no stars?). Create it.
                // Note: Material CSS might hide .md-source__facts on small screens.
                facts = document.createElement("ul");
                facts.className = "md-source__facts";
                sourceRepository.appendChild(facts);
            }

            // Create our fact item
            var li = document.createElement("li");
            li.className = "md-source__fact";
            li.id = "busuanzi_container_site_pv_custom"; // Wrapper ID

            // Busuanzi content
            li.innerHTML = `
                <span id="busuanzi_container_site_pv" style="display:none">
                    Visitors: <span id="busuanzi_value_site_pv">--</span>
                </span>
            `;

            facts.appendChild(li);

        } else if (headerInner) {
            // Fallback: No repository block found. Insert in header as before.
            var counter = document.createElement("div");
            counter.id = "busuanzi_container_site_pv_custom";
            counter.className = "md-header__option";
            counter.style.marginLeft = "10px";
            counter.style.marginRight = "10px";
            counter.style.fontSize = "0.7rem";
            counter.style.color = "inherit";

            counter.innerHTML = `
                <span id="busuanzi_container_site_pv" style="display:none">
                    Visitors: <span id="busuanzi_value_site_pv">--</span>
                </span>
            `;

            var search = document.querySelector(".md-search");
            var source = document.querySelector(".md-header__source");

            if (source) {
                 headerInner.insertBefore(counter, source);
            } else if (search) {
                 headerInner.insertBefore(counter, search);
            } else {
                 headerInner.appendChild(counter);
            }
        }
    }

    // Run insertion immediately
    insertCounter();

    // 3. Observe header for changes
    // This is crucial because Material loads repo stats asynchronously.
    // When stats load, .md-source__facts might be replaced or updated.
    var observer = new MutationObserver(function(mutations) {
        // We just check if our element is still there. If not, re-insert.
        // Note: If Material wipes innerHTML of facts, our element dies.
        insertCounter();
    });

    var header = document.querySelector(".md-header");
    if (header) {
        observer.observe(header, { childList: true, subtree: true });
    }
}
