// static/js/policyTree.js
// D3 visualisation for policy JSON (node-link graph)

  // Optional external zoom control hook
  function attachZoomControls(svgSelector, zoomInstance, graphGroup) {
    console.log(svgSelector)
    document.getElementById('zoom-in').addEventListener('click', () => {
      zoomInstance.scaleBy(d3.select(svgSelector).transition().duration(300), 1.2);
    });
    document.getElementById('zoom-out').addEventListener('click', () => {
      zoomInstance.scaleBy(d3.select(svgSelector).transition().duration(300), 0.8);
    });
    document.getElementById('zoom-reset').addEventListener('click', () => {
      d3.select(svgSelector)
        .transition()
        .duration(400)
        .call(zoomInstance.transform, d3.zoomIdentity);
    });
  }


/**
 * Render a policy decision graph using D3.js
 * @param {Object} data - Graph data containing nodes[] and links[]
 * @param {string|HTMLElement} target - Target SVG element or its ID
 * @param {Object} options - Optional layout/config overrides
 */
function renderPolicyGraph(data, targetId, options = {}) {
    const config = {
      width: options.width || 1000,
      height: options.height || 1600,
      nodeWidth: options.nodeWidth || 180,
      nodeHeight: options.nodeHeight || 60,
      levelHeight: options.levelHeight || 130,
      rootNode: options.rootNode || "age_check",
      colorScheme: options.colorScheme || [
        "#4CAF50", "#FF9800", "#2196F3", "#9C27B0", "#E91E63", "#00BCD4", "#F44336"
      ],
    };
  
    const svgEl = typeof targetId === "string" ? document.getElementById(targetId) : targetId;
    if (!svgEl) {
      console.error("renderPolicyGraph: target element not found.");
      return;
    }
  
    const svg = d3.select(svgEl)
      .attr("width", config.width)
      .attr("height", config.height)
      .attr("viewBox", [0, 0, config.width, config.height]);
  
    svg.selectAll("*").remove(); // Clear previous content

    // Re-select after clearing
    const svgRoot = d3.select(`#${targetId}`)
        .attr("width", config.width)
        .attr("height", config.height)
        .attr("viewBox", [0, 0, config.width, config.height]);

  
    const graphGroup = svgRoot.append("g").attr("class", "graph");
  
    // Define arrow marker for links
    const defs = svgRoot.append("defs");
    defs.append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 10)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#666");
  
    // Color scale by group
    const groups = [...new Set(data.nodes.map(n => n.group))];
    const colorScale = d3.scaleOrdinal()
      .domain(groups)
      .range(config.colorScheme.slice(0, groups.length));
  
    // ---- Layout calculation ----
    const nodeMap = new Map(data.nodes.map(n => [n.id, { ...n, level: 0 }]));
    const levels = {};
    const root = config.rootNode;
    const queue = [root];
    nodeMap.get(root).level = 0;
  
    while (queue.length) {
      const current = queue.shift();
      const currentLevel = nodeMap.get(current).level;
      data.links
        .filter(l => l.source === current)
        .forEach(l => {
          const target = l.target;
          if (!nodeMap.get(target).level || nodeMap.get(target).level <= currentLevel) {
            nodeMap.get(target).level = currentLevel + 1;
          }
          if (!queue.includes(target)) queue.push(target);
        });
    }
  
    nodeMap.forEach(node => {
      if (!levels[node.level]) levels[node.level] = [];
      levels[node.level].push(node);
    });
  
    Object.keys(levels).forEach(level => {
      const nodesInLevel = levels[level];
      const spacing = config.width / (nodesInLevel.length + 1);
      nodesInLevel.forEach((node, i) => {
        node.x = spacing * (i + 1);
        node.y = 100 + level * config.levelHeight;
      });
    });
  
    // ---- Draw links ----
    const linkGroup = svg.append("g").attr("class", "links");
  
    data.links.forEach(link => {
      const source = nodeMap.get(link.source);
      const target = nodeMap.get(link.target);
  
      const path = linkGroup.append("path")
        .attr("class", "link")
        .attr("d", () => {
          const sx = source.x;
          const sy = source.y + config.nodeHeight / 2;
          const tx = target.x;
          const ty = target.y - config.nodeHeight / 2;
          const my = (sy + ty) / 2;
          return `M ${sx} ${sy} C ${sx} ${my}, ${tx} ${my}, ${tx} ${ty}`;
        })
        .attr("fill", "none")
        .attr("stroke", "#999")
        .attr("stroke-width", 1.5)
        .attr("marker-end", "url(#arrowhead)");
  
      // Label position
      const labelX = (source.x + target.x) / 2;
      const labelY = (source.y + target.y) / 2;
  
      // Label background
      linkGroup.append("rect")
        .attr("x", labelX - 40)
        .attr("y", labelY - 10)
        .attr("width", 80)
        .attr("height", 20)
        .attr("rx", 3)
        .attr("fill", "white")
        .attr("opacity", 0.8);
  
      linkGroup.append("text")
        .attr("x", labelX)
        .attr("y", labelY + 4)
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .attr("fill", "#333")
        .text(link.label);
    });
  
    // ---- Draw nodes ----
    const nodeGroup = svg.append("g").attr("class", "nodes");
  
    const nodes = nodeGroup.selectAll("g.node")
      .data(Array.from(nodeMap.values()))
      .join("g")
      .attr("class", "node")
      .attr("transform", d => `translate(${d.x - config.nodeWidth / 2}, ${d.y - config.nodeHeight / 2})`);
  
    nodes.append("rect")
      .attr("width", config.nodeWidth)
      .attr("height", config.nodeHeight)
      .attr("rx", 10)
      .attr("fill", d => colorScale(d.group))
      .attr("stroke", "#444")
      .attr("stroke-width", 1.2);
  
    nodes.append("text")
      .attr("x", config.nodeWidth / 2)
      .attr("y", config.nodeHeight / 2 - 5)
      .attr("text-anchor", "middle")
      .attr("font-size", "13px")
      .attr("font-weight", "600")
      .attr("fill", "#fff")
      .text(d => d.name);
  
    nodes.append("text")
      .attr("x", config.nodeWidth / 2)
      .attr("y", config.nodeHeight / 2 + 12)
      .attr("text-anchor", "middle")
      .attr("font-size", "11px")
      .attr("fill", "#f5f5f5")
      .text(d => d.group);
  
    // ---- Legend ----
    const legend = svg.append("g")
      .attr("class", "legend")
      .attr("transform", `translate(20, 20)`);
  
    groups.forEach((group, i) => {
      const row = legend.append("g")
        .attr("transform", `translate(0, ${i * 25})`);
  
      row.append("rect")
        .attr("width", 15)
        .attr("height", 15)
        .attr("fill", colorScale(group));
  
      row.append("text")
        .attr("x", 22)
        .attr("y", 12)
        .text(group)
        .attr("font-size", "12px")
        .attr("fill", "#333");
    });

    // --- Zoom & Pan ---
    const zoom = d3.zoom()
    .scaleExtent([0.4, 2.5])
    .on("zoom", (event) => {
        graphGroup.attr("transform", event.transform);
    });

    svgRoot.call(zoom);


    // Optional initial center/scale
    const initialScale = 0.9;
    const initialTranslate = [100, 40];
    svgRoot.call(zoom.transform, d3.zoomIdentity.translate(...initialTranslate).scale(initialScale));

    attachZoomControls(`#${targetId}`, zoom, graphGroup);

  }


  // Export to global scope
  window.renderPolicyGraph = renderPolicyGraph;
  
