// Function to fetch the current state from the server and update the UI
async function updateState() {
    try {
        // Fetch data from both API endpoints simultaneously
        const [stateResponse, graphResponse] = await Promise.all([
            fetch('/api/state'),
            fetch('/api/wait_for_graph')
        ]);
        const state = await stateResponse.json();
        const graph = await graphResponse.json();

        // Update all UI components based on the fetched data
        updateUI(state);
        drawGraph(graph);

    } catch (error) {
        console.error('Error fetching state:', error);
    }
}

// Function to update the main UI components
function updateUI(state) {
    // Helper function to apply the correct status class based on the process's status
    const setStatusClass = (element, status) => {
        // First, remove any existing status classes to avoid conflicts
        element.classList.remove('process-running', 'process-blocked', 'process-waiting');
        
        if (!status) return;
        const normalizedStatus = status.toLowerCase();

        // Add the correct class based on the status from the backend
        if (normalizedStatus === 'running') {
            element.classList.add('process-running');
        } else if (normalizedStatus === 'blocked') {
            element.classList.add('process-blocked');
        } else if (normalizedStatus === 'waiting') { 
            element.classList.add('process-waiting');
        }
    };

    const setHandlerStatus = (element, status) => {
        // Reset old state
        element.classList.remove("handler-empty", "handler-running");

        if (!status) return;

        if (status.toLowerCase() === "empty") {
            element.classList.add("handler-empty");
        } else if (status.toLowerCase() === "running") {
            element.classList.add("handler-running");
        }
    };

    // Update the Active User Sessions (Handler frames)
    const handlerFrames = document.querySelectorAll('.handler-frame');
    state.handler_frames.forEach((frame_str, index) => {
        // Assuming the frame string is in the format "User_X (Status)"
        const match = frame_str.match(/\(([^)]+)\)/);
        const status = match ? match[1] : null;
        
        handlerFrames[index].textContent = frame_str;
        // Set the color based on the extracted status
        setStatusClass(handlerFrames[index], status);
    });


    // Update the Waiting Queue
    const waitingQueueContainer = document.querySelector('.queue-blocks-row');
    waitingQueueContainer.innerHTML = ''; // Clear the existing queue to prevent duplicates
    state.waiting_queue.forEach(item => {
        const queueBlock = document.createElement('div');
        queueBlock.classList.add('queue-block');
        queueBlock.textContent = item;
        
        // All items in the waiting queue are by definition in a 'waiting' state
        setStatusClass(queueBlock, 'Waiting');
        
        waitingQueueContainer.appendChild(queueBlock);
    });

    // Update the Resource Manager's status blocks
    const resourceStatusBlocks = document.querySelectorAll('.resource-status-block');
    state.resources.forEach((res, index) => {
        const isFree = res === 'Free';
        resourceStatusBlocks[index].textContent = isFree ? 'Free' : res;
        resourceStatusBlocks[index].style.backgroundColor = isFree ? '#d4edda' : '#f8d7da'; // Light green for free, light red for held
        resourceStatusBlocks[index].style.color = isFree ? '#155724' : '#721c24'; // Dark green for free, dark red for held
    });

    // Update the System Logs
    const logOutput = document.getElementById('log-output');
    logOutput.textContent = state.log.join('\n');
    logOutput.scrollTop = logOutput.scrollHeight; // Auto-scroll to the bottom

    // Update Server Utilization
    const utilizationPercentage = document.getElementById('utilization-percentage');
    const utilizationBar = document.getElementById('utilization-bar');
    utilizationPercentage.textContent = `${state.utilization}%`;
    utilizationBar.style.width = `${state.utilization}%`;

    // Update button states
    document.getElementById('start-btn').disabled = state.running;
    document.getElementById('pause-btn').disabled = !state.running;
    document.getElementById('resume-btn').disabled = state.running;
    document.getElementById('stop-btn').disabled = !state.running;
}

// Custom function to draw the wait-for graph on a canvas
function drawGraph(graph) {
    const canvas = document.getElementById('wait-for-graph-canvas');
    const ctx = canvas.getContext('2d');
    
    // Set canvas dimensions
    canvas.width = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Node positions (fixed circular layout)
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = Math.min(centerX, centerY) * 0.8;
    const nodePositions = {};

    // Get all unique nodes for drawing
    const allNodes = new Set();
    graph.nodes.forEach(node => allNodes.add(node.id));

    // Create a mapping of node IDs to their positions on the circle
    const nodesArray = Array.from(allNodes);
    nodesArray.forEach((nodeId, index) => {
        const angle = (index / nodesArray.length) * 2 * Math.PI;
        nodePositions[nodeId] = {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle)
        };
    });

graph.edges.forEach(edge => {
    if (nodePositions[edge.from] && nodePositions[edge.to]) {
        const from = nodePositions[edge.from];
        const to = nodePositions[edge.to];
        const angle = Math.atan2(to.y - from.y, to.x - from.x);

        // --- Compute endpoint at edge of target circle ---
        const nodeRadius = 15;  // same radius you use for ctx.arc
        const arrowX = to.x - nodeRadius * Math.cos(angle);
        const arrowY = to.y - nodeRadius * Math.sin(angle);

        // --- Draw the edge line ---
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(arrowX, arrowY);  // stop BEFORE the node
        ctx.strokeStyle = '#495057';
        ctx.lineWidth = 2;
        ctx.stroke();

        // --- Draw the arrowhead ---
        const headlen = 12;  // arrowhead size
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - headlen * Math.cos(angle - Math.PI / 6),
                   arrowY - headlen * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(arrowX - headlen * Math.cos(angle + Math.PI / 6),
                   arrowY - headlen * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fillStyle = '#495057';
        ctx.fill();
    }
});


    // Draw the nodes (circles)
    graph.nodes.forEach(node => {
        if (nodePositions[node.id]) {
            const pos = nodePositions[node.id];
            
            // Draw circle
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, 15, 0, 2 * Math.PI);
            ctx.fillStyle = node.is_deadlocked ? '#dc3545' : '#17a2b8'; // Red for deadlock, blue for others
            ctx.fill();
            ctx.strokeStyle = '#343a40';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Draw label
            ctx.fillStyle = '#343a40';
            ctx.font = '12px Segoe UI, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText(node.label, pos.x, pos.y - 20);
        }
    });
}

// Add event listeners to control buttons
let updateInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('start-btn').addEventListener('click', () => {
        fetch('/api/start', { method: 'POST' }).then(() => {
            if (!updateInterval) {
                updateInterval = setInterval(updateState, 1000);
            }
        });
    });

    document.getElementById('pause-btn').addEventListener('click', () => {
        fetch('/api/pause', { method: 'POST' });
    });

    document.getElementById('resume-btn').addEventListener('click', () => {
        fetch('/api/resume', { method: 'POST' });
    });

    document.getElementById('stop-btn').addEventListener('click', () => {
        fetch('/api/stop', { method: 'POST' });
    });

    // Initial state update when the page loads
    updateState();
    if (!updateInterval) {
        updateInterval = setInterval(updateState, 1000);
    }
});