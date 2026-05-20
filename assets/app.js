/**
 * TripGenius Frontend Application
 */

const API_BASE = 'http://localhost:8000/api';

// ============== DOM Elements ==============
const destinationInput = document.getElementById('destination');
const daysInput = document.getElementById('days');
const budgetInput = document.getElementById('budget');
const styleInputs = document.querySelectorAll('input[name="style"]');
const generateBtn = document.getElementById('generateBtn');
const resultSection = document.getElementById('resultSection');
const resultTitle = document.getElementById('resultTitle');
const resultContent = document.getElementById('resultContent');
const resetBtn = document.getElementById('resetBtn');
const loadingOverlay = document.getElementById('loadingOverlay');

// ============== State ==============
let currentItinerary = null;

// ============== Event Listeners ==============
generateBtn.addEventListener('click', handleGenerate);
resetBtn.addEventListener('click', handleReset);

// ============== Main Handlers ==============
async function handleGenerate() {
    const destination = destinationInput.value.trim();
    const days = parseInt(daysInput.value) || 3;
    const budget = parseInt(budgetInput.value) || 5000;
    const style = document.querySelector('input[name="style"]:checked').value;

    if (!destination) {
        alert('请输入目的地');
        destinationInput.focus();
        return;
    }

    setLoading(true);

    try {
        const response = await fetch(`${API_BASE}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                destination,
                days,
                budget,
                style,
            }),
        });

        const data = await response.json();

        if (data.success && data.data) {
            currentItinerary = data.data;
            renderResult(data.data);
        } else {
            alert('生成失败: ' + (data.error || '未知错误'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('请求失败，请确保后端服务已启动 (python -m uvicorn src.api.main:app --reload)');
    } finally {
        setLoading(false);
    }
}

function handleReset() {
    destinationInput.value = '';
    daysInput.value = '3';
    budgetInput.value = '5000';
    document.querySelector('input[name="style"][value="chill"]').checked = true;
    resultSection.style.display = 'none';
    currentItinerary = null;
}

// ============== UI Functions ==============
function setLoading(loading) {
    generateBtn.disabled = loading;
    generateBtn.querySelector('.btn-text').style.display = loading ? 'none' : 'inline';
    generateBtn.querySelector('.btn-loading').style.display = loading ? 'inline' : 'none';
    loadingOverlay.style.display = loading ? 'flex' : 'none';
}

function renderResult(itinerary) {
    resultTitle.textContent = itinerary.title || '行程规划';
    resultSection.style.display = 'block';

    let html = '';

    // Render itinerary days
    if (itinerary.itinerary && itinerary.itinerary.length > 0) {
        html += '<div class="itinerary-list">';

        itinerary.itinerary.forEach(day => {
            html += `
            <div class="itinerary-day">
                <div class="day-header">Day ${day.day}: ${day.theme || ''}</div>
                <div class="day-content">
                    ${renderDaySection('上午', day.morning)}
                    ${renderDaySection('下午', day.afternoon)}
                    ${renderDaySection('晚上', day.evening)}
                    ${renderFood(day.food)}
                    ${renderTips(day.tips)}
                </div>
            </div>
            `;
        });

        html += '</div>';
    }

    // Render summary
    html += `
    <div class="summary-section">
        <h3 style="margin-bottom: 16px;">行程概览</h3>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-label">目的地</div>
                <div class="summary-value">${itinerary.destination || destinationInput.value}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">行程天数</div>
                <div class="summary-value">${itinerary.days || daysInput.value}天</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">风格</div>
                <div class="summary-value">${getStyleName(itinerary.style)}</div>
            </div>
            <div class="summary-item">
                <div class="summary-label">预算</div>
                <div class="summary-value">${itinerary.total_cost || budgetInput.value}元</div>
            </div>
        </div>
    </div>
    `;

    // Render highlights
    if (itinerary.highlights && itinerary.highlights.length > 0) {
        html += `
        <div class="summary-section">
            <h3 style="margin-bottom: 12px;">行程亮点</h3>
            <ul style="padding-left: 20px; color: var(--text-light);">
                ${itinerary.highlights.map(h => `<li>${h}</li>`).join('')}
            </ul>
        </div>
        `;
    }

    resultContent.innerHTML = html;
}

function renderDaySection(title, content) {
    if (!content || !content.spot) return '';

    return `
    <div class="day-section">
        <div class="day-section-title">${title}</div>
        <div class="day-section-content">
            <strong>${content.spot}</strong>
            ${content.tips ? `<br/><span style="color: var(--text-light); font-size: 0.875rem;">💡 ${content.tips}</span>` : ''}
            ${content.cost ? `<span style="color: var(--success); font-size: 0.875rem;"> ¥${content.cost}</span>` : ''}
        </div>
    </div>
    `;
}

function renderFood(food) {
    if (!food || food.length === 0) return '';

    return `
    <div class="day-section">
        <div class="day-section-title">美食推荐</div>
        <ul class="food-list">
            ${food.map(f => `<li>${f.meal || f}</li>`).join('')}
        </ul>
    </div>
    `;
}

function renderTips(tips) {
    if (!tips || tips.length === 0) return '';

    return `
    <div class="day-section">
        <div class="day-section-title">小贴士</div>
        <div class="day-section-content" style="font-size: 0.875rem; color: var(--text-light);">
            ${tips.map(t => `• ${t}`).join('<br/>')}
        </div>
    </div>
    `;
}

function getStyleName(style) {
    const styleMap = {
        'chill': '🌿 休闲',
        '美食': '🍜 美食',
        '打卡': '📍 打卡',
        '出片': '📷 出片',
    };
    return styleMap[style] || style;
}
