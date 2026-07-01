import os
import time
import sqlite3
import threading
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

# Путь к базе данных внутри автономного Android-приложения
DB_NAME = os.path.join(os.path.expanduser("~"), "workout_diary_stable_v120.db")

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS exercise_base (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, is_active INTEGER DEFAULT 1)')
        c.execute('CREATE TABLE IF NOT EXISTS daily_plans (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, exercise_name TEXT, planned_sets INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS workout_history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, exercise_name TEXT, set_num INTEGER, reps INTEGER, weight REAL, start_time TEXT, duration INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY AUTOINCREMENT, template_name TEXT, exercise_name TEXT, sets INTEGER)')
        conn.commit()
        
        c.execute("SELECT COUNT(*) FROM exercise_base WHERE is_active = 1")
        if c.fetchone() == 0:
            init_ex = ["Гоблет-приседания", "Румынская тяга", "Ягодичный мостик", "Болгарские выпады", "Жим на полу", "Тяга штанги в наклоне", "Тяга гири к поясу", "Планка", "Скручивания", "Боковая планка"]
            for e in init_ex:
                try:
                    c.execute("INSERT INTO exercise_base (name, is_active) VALUES (?, 1)", (e,))
                except sqlite3.IntegrityError:
                    pass
            conn.commit()

init_db()
current_set_start = {"time": None}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Дневник</title>
    <style>
        body{font-family:sans-serif;background:#f4f4f9;padding:10px;}
        .card{background:white;padding:12px;border-radius:8px;margin-bottom:10px;box-shadow:0 2px 5px rgba(0,0,0,0.05);}
        select,input,button{width:100%;padding:10px;margin:4px 0;border-radius:6px;border:1px solid #ddd;box-sizing:border-box;}
        .row{display:flex;gap:6px;}
        .box{background:#f9f9f9;padding:10px;border-radius:4px;margin:4px 0;font-size:14px;border-left:4px solid #5e35b1;transition:0.2s;display:flex;justify-content:space-between;align-items:center;}
        .selectable{cursor:pointer;}
        .selected-ex{background:#e1d5f5 !important;border-left:6px solid #7b1fa2 !important;font-weight:bold;}
        .btn-del{background:#c62828;color:white;border:none;padding:5px 12px;border-radius:6px;font-size:14px;font-weight:bold;width:auto;margin:0;cursor:pointer;margin-left:auto;}
        .btn-vest{background:#0288d1;color:white;font-weight:bold;margin-top:5px;}
        .btn-icon{width:45px; min-width:45px; font-weight:bold; color:white; font-size:16px; cursor:pointer;}
        .btn-inline{padding:2px 6px; font-size:11px; width:auto; margin:0 2px; display:inline-block; background:#7b1fa2; color:white; font-weight:bold; cursor:pointer;}
        .tab-btn{background:#e0e0e0; color:black; font-weight:bold; border:none; margin:0;}
        .active-tab{background:#5e35b1 !important; color:white !important;}
        .stat-row{padding:8px 0; border-bottom:1px solid #eee; font-size:13px; line-height:1.4;}
        .header-row{display:flex; justify-content:space-between; align-items:center;}
        .btn-header-add{background:#7b1fa2; color:white; border:none; border-radius:50%; width:28px; height:28px; font-size:16px; font-weight:bold; cursor:pointer; display:flex; align-items:center; justify-content:center; padding:0; margin:0;}
        
        .grid-stats-2{display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px;}
        .mini-card{background:#e8f5e9; padding:12px 8px; border-radius:8px; font-size:13px; font-weight:bold; color:#2e7d32; box-shadow:0 1px 3px rgba(0,0,0,0.05); display:flex; justify-content:space-between; align-items:center; box-sizing:border-box;}
        .mini-card span{font-size:18px; color:#1b5e20; font-weight:bold; margin-left:6px;}
        
        .stat-rank-item{background:#fafafa; border:1px solid #ddd; padding:10px; border-radius:6px; margin:5px 0; cursor:pointer; transition:0.15s;}
        .stat-rank-title{font-weight:bold; display:flex; justify-content:space-between; color:#333; font-size:13px;}
        .stat-rank-details{margin-top:8px; padding-top:6px; border-top:1px dotted #ccc; display:none; font-size:12px; color:#444;}
        .badge-rank{background:#e1d5f5; color:#311b92; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold;}
        .summary-box{background:#f1f8e9; border-left:4px solid #2e7d32; padding:6px; border-radius:4px; margin-bottom:5px; font-size:12px;}
    </style>
</head><body>

<div class="row" style="margin-bottom:10px;">
    <button id="tab_workout_btn" class="tab-btn active-tab" onclick="switchTab('workout')">💪 Тренировка</button>
    <button id="tab_stat_btn" class="tab-btn" onclick="switchTab('stat')">📊 Статистика</button>
</div>

<div id="tab_workout">
    <div class="card">
        <b>Календарь:</b>
        <div class="row">
            <input type="date" id="target_date" onchange="loadDayData()">
            <button style="width:35%; background:#777; color:white; font-weight:bold;" onclick="setTodayDate()">Сегодня</button>
        </div>
        <button class="btn-vest" onclick="logVestibular()">🧘 Вестибулярка</button>
    </div>

    <div class="card">
        <b>Конструктор программы:</b>
        <div class="row" style="margin-bottom:0;">
            <input type="text" id="exercise_search_input" list="exercise_datalist" placeholder="Поиск или ввод упражнения..." style="margin:0;">
            <button class="btn-icon" style="background:#ffb300; color:black;" onclick="addToDailyPlan()">➕</button>
            <button class="btn-icon" style="background:#7b1fa2;" onclick="addCustomToBase()">⭐</button>
            <button class="btn-icon" style="background:#e65100;" onclick="archiveExercise()">🗄️</button>
        </div>
        <datalist id="exercise_datalist">
            {% for ex in exercises %}<option value="{{ ex }}"></option>{% endfor %}
        </datalist>
    </div>

    <div class="card">
        <div class="header-row">
            <b>План на день:</b>
            <button class="btn-header-add" onclick="saveCurrentPlanAsTemplate()" title="Сохранить этот план как комплекс">+</button>
        </div>
        <div id="daily_plan_list"></div>
    </div>

    <div class="card">
        <b>Выполнение подхода<span id="active_ex_title"> (Упражнение не выбрано)</span></b>
        <div class="row">
            <div><small>Вес (0-статика)</small><input type="number" id="weight" value="14"></div>
            <div><small>Подх.</small><input type="number" id="set_num" value="1"></div>
            <div><small>Повт.</small><input type="number" id="reps" value="12"></div>
        </div>
        <div class="row">
            <button style="background:#2e7d32; color:white; width:40%;" id="start_btn" onclick="startSet()">Старт</button>
            <button style="background:#1565c0; color:white; width:40%;" id="rest_btn" onclick="toggleRest()">Отдых (60с)</button>
            <button style="background:#7b1fa2; color:white; width:20%; font-weight:bold;" onclick="add30Seconds()">+30с</button>
        </div>
    </div>

    <div class="card"><b>Выполнено за день:</b><div id="history_list"></div></div>
</div>

<div id="tab_stat" style="display:none;">
    <div class="grid-stats-2">
        <div class="mini-card">Тренировки<span id="stat_total_days">0</span></div>
        <div class="mini-card">Вестибулярка<span id="stat_total_vest">0</span></div>
    </div>
    
    <div class="card">
        <b>🏆 Топ-5 частых упражнений:</b>
        <div id="top_exercises_container" style="margin-top:5px;"></div>
        
        <b style="display:block; margin-top:12px;">🔍 Посмотреть другое упражнение:</b>
        <select id="stat_exercise_select" onchange="loadSingleExerciseStats()">
            <option value="">-- Выберите из списка --</option>
            {% for ex in exercises %}<option value="{{ ex }}">{{ ex }}</option>{% endfor %}
        </select>
        <div id="single_exercise_stats_box" class="stat-rank-item" style="display:none; margin-top:8px;"></div>
    </div>
</div>
</body>
</html>
"""
JS_CODE = """
<script>
let timerInterval, timeLeft = 60, defaultRestTime = 60, isResting = false, exerciseInterval, exerciseSeconds = 0, isExercising = false;
let currentlyExecutingExercise = ""; let globalHistory = [];

window.onload = function(){ setTodayDate(); };

function switchTab(tabName) {
    if(tabName === 'workout') {
        document.getElementById('tab_workout').style.display = 'block';
        document.getElementById('tab_stat').style.display = 'none';
        document.getElementById('tab_workout_btn').classList.add('active-tab');
        document.getElementById('tab_stat_btn').classList.remove('active-tab');
        loadDayData();
    } else {
        document.getElementById('tab_workout').style.display = 'none';
        document.getElementById('tab_stat').style.display = 'block';
        document.getElementById('tab_workout_btn').classList.remove('active-tab');
        document.getElementById('tab_stat_btn').classList.add('active-tab');
        loadGlobalStats();
    }
}

function loadGlobalStats() {
    fetch("/get_global_stats").then(res=>res.json()).then(data=>{
        document.getElementById("stat_total_days").innerText = data.total_days;
        document.getElementById("stat_total_vest").innerText = data.total_vest;
        
        const container = document.getElementById("top_exercises_container");
        container.innerHTML = "";
        
        if (data.top_exercises.length === 0) {
            container.innerHTML = "<small style='color:#777;'>История тренировок пуста</small>";
            return;
        }
        
        data.top_exercises.forEach((item, index) => {
            let medal = index === 0 ? "🥇 " : index === 1 ? "🥈 " : index === 2 ? "🥉 " : "💪 ";
            let block = document.createElement("div");
            block.className = "stat-rank-item";
            
            block.innerHTML = '<div class="stat-rank-title" onclick="toggleDetails(this)">' +
                '<span>' + medal + '<b>' + item.name + '</b></span>' +
                '<span class="badge-rank">Дней: ' + item.days_cnt + '</span>' +
                '</div>';
                
            let details = document.createElement("div");
            details.className = "stat-rank-details";
            
            if (parseFloat(item.max_weight) === 0) {
                details.innerHTML = '<div class="summary-box">⏱️ <b>Рекорд выносливости:</b> ' + item.max_duration + 'с</div>';
            } else {
                let onepm = Math.round(parseFloat(item.max_weight) * (1 + parseInt(item.max_reps) / 30));
                details.innerHTML = '<div class="summary-box">🏋️ <b>Личный рекорд:</b> ' + item.max_weight + ' кг на ' + item.max_reps + ' повт.<br>⚡ <b>Сила (1ПМ):</b> ~' + onepm + ' кг</div>';
            }
            
            item.history.forEach(h => {
                let line = parseFloat(h.w) === 0 ? "⏱️ " + h.dur + "с" : "🏋️ " + h.w + " кг x " + h.r + " повт. (Подходов: " + h.sets + ")";
                details.innerHTML += '<div class="stat-row">📅 <b>' + h.date + '</b> — ' + line + '</div>';
            });
            
            block.appendChild(details);
            container.appendChild(block);
        });
    });
}

function loadSingleExerciseStats() {
    const ex = document.getElementById("stat_exercise_select").value;
    const box = document.getElementById("single_exercise_stats_box");
    if (!ex) { box.style.display = "none"; return; }
    
    fetch("/get_single_ex_stat?name=" + encodeURIComponent(ex)).then(res=>res.json()).then(data=>{
        box.innerHTML = "";
        box.style.display = "block";
        
        let title = document.createElement("div");
        title.className = "stat-rank-title";
        title.innerHTML = '<span>🔍 <b>' + data.name + '</b></span><span class="badge-rank">Дней: ' + data.days_cnt + '</span>';
        box.appendChild(title);
        
        let details = document.createElement("div");
        details.className = "stat-rank-details";
        details.style.display = "block";
        
        if (data.days_cnt === 0) {
            details.innerHTML = "<small style='color:#777; display:block; padding:5px;'>Упражнение еще не выполнялось</small>";
        } else {
            if (parseFloat(data.max_weight) === 0) {
                details.innerHTML = '<div class="summary-box">⏱️ <b>Рекорд выносливости:</b> ' + data.max_duration + 'с</div>';
            } else {
                let onepm = Math.round(parseFloat(data.max_weight) * (1 + parseInt(data.max_reps) / 30));
                details.innerHTML = '<div class="summary-box">🏋️ <b>Личный рекорд:</b> ' + data.max_weight + ' кг на ' + data.max_reps + ' повт.<br>⚡ <b>Сила (1ПМ):</b> ~' + onepm + ' кг</div>';
            }
            data.history.forEach(h => {
                let line = parseFloat(h.w) === 0 ? "⏱️ " + h.dur + "с" : "🏋️ " + h.w + " кг x " + h.r + " повт. (Подходов: " + h.sets + ")";
                details.innerHTML += '<div class="stat-row">📅 <b>' + h.date + '</b> — ' + line + '</div>';
            });
        }
        box.appendChild(details);
    });
}

// Концовка скриптов вынесена в JS_CODE_2 во избежание переполнения буфера
</script>
"""

JS_CODE_2 = """
<script>
function toggleDetails(element) {
    let details = element.nextElementSibling;
    details.style.display = (details.style.display === "block") ? "none" : "block";
    element.parentElement.style.background = (details.style.display === "block") ? "#f1e9fc" : "#fafafa";
}

function setTodayDate(){ 
    document.getElementById("target_date").value = new Date().toISOString().split("T")[0]; 
    currentlyExecutingExercise = ""; 
    document.getElementById("active_ex_title").innerText = " (Упражнение не выбрано)"; 
    loadDayData(); 
}

function add30Seconds(){ 
    if(isResting){ 
        timeLeft += 30; 
        document.getElementById("rest_btn").innerText = "Отдых: " + timeLeft + "c"; 
    } else { 
        defaultRestTime += 30; 
        document.getElementById("rest_btn").innerText = "Отдых ("+defaultRestTime+"с)"; 
    } 
}

function logVestibular() {
    const d = document.getElementById("target_date").value;
    fetch("/save_set", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({date: d, ex: "🧘 Вестибулярная гимнастика", weight: 0, setNum: 1, reps: 0, duration: 300})
    }).then(() => loadDayData());
}

function archiveExercise(){ 
    const ex = document.getElementById("exercise_search_input").value.trim(); 
    if(!ex){ alert("Сначала введите или выберите упражнение в строке поиска!"); return; } 
    if(confirm('Скрыть упражнение "' + ex + '" из списка поиска? В истории тренировок оно сохранится.')){ 
        fetch("/archive_exercise",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:ex})}).then(()=>location.reload()); 
    } 
}

function playBeep() { 
    try { 
        const ctx = new (window.AudioContext || window.webkitAudioContext)(); 
        function tone(freq, start, dur) { 
            const osc = ctx.createOscillator(); 
            const gain = ctx.createGain(); 
            osc.type = "sine"; 
            osc.frequency.value = freq; 
            osc.connect(gain); 
            gain.connect(ctx.destination); 
            gain.gain.setValueAtTime(0.1, start); 
            gain.gain.exponentialRampToValueAtTime(0.0001, start + dur); 
            osc.start(start); 
            osc.stop(start + dur); 
        } 
        tone(880, ctx.currentTime, 0.15); 
        tone(880, ctx.currentTime + 0.2, 0.15); 
    } catch(e) { console.log(e); } 
}

function loadDayData(){
    const d = document.getElementById("target_date").value;
    fetch('/get_day_data?date=' + d).then(res=>res.json()).then(data=>{
        globalHistory = data.history;
        const p = document.getElementById("daily_plan_list"); 
        p.innerHTML = data.plan.length === 0 ? "План пуст" : "";
        
        data.plan.forEach(i=>{
            const isSelected = (i.ex === currentlyExecutingExercise) ? "selected-ex" : "";
            p.innerHTML += '<div class="box selectable ' + isSelected + '" onclick="selectExerciseForExecution(\\'' + i.ex + '\\')">' +
                '<span><b>' + i.ex + '</b> - План: ' + i.sets + ' подх. ' +
                    '<button class="btn-inline" onclick="changeSets(event, \\'' + i.ex + '\\', 1)">▲</button>' +
                    '<button class="btn-inline" onclick="changeSets(event, \\'' + i.ex + '\\', -1)">▼</button>' +
                '</span>' +
                '<button class="btn-del" onclick="deletePlanItem(event, \\'' + i.ex + '\\')">-</button>' +
            '</div>';
        });
        
        const hList = document.getElementById("history_list"); 
        hList.innerHTML = data.history.length === 0 ? "Ничего не выполнено" : "";
        
        let countsMap = {};
        
        data.history.forEach(i=>{
            if (!countsMap[i.ex]) { countsMap[i.ex] = 0; }
            countsMap[i.ex]++;
            let currentSetIndex = countsMap[i.ex];
            
            if(i.ex === "🧘 Вестибулярная гимнастика"){
                hList.innerHTML += '<div class="box"><span><b>' + i.ex + '</b> | Время: 5 мин</span><button class="btn-del" onclick="deleteHistoryItem(event, ' + i.id + ')">-</button></div>';
            } else if(parseFloat(i.weight) === 0) {
                hList.innerHTML += '<div class="box"><span><b>' + i.ex + '</b> (Подход ' + currentSetIndex + ') | Время: ' + i.duration + 'с<br><small>Старт: ' + i.time + '</small></span><button class="btn-del" onclick="deleteHistoryItem(event, ' + i.id + ')">-</button></div>';
            } else {
                hList.innerHTML += '<div class="box"><span><b>' + i.ex + '</b> (Подход ' + currentSetIndex + ') - ' + i.reps + ' повт. (' + i.weight + ' кг)<br><small>Старт: ' + i.time + ' | Подход: ' + i.duration + 'с</small></span><button class="btn-del" onclick="deleteHistoryItem(event, ' + i.id + ')">-</button></div>';
            }
        });
        updateNextSetNumber();
    });
}

function changeSets(event, exName, delta){ 
    event.stopPropagation(); 
    const d = document.getElementById("target_date").value; 
    fetch("/update_plan_sets", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({date:d, ex:exName, delta:delta})}).then(()=>loadDayData()); 
}
function selectExerciseForExecution(name) { 
    currentlyExecutingExercise = name; 
    document.getElementById("active_ex_title").innerText = ": " + name; 
    defaultRestTime = 60; 
    if(!isResting){ document.getElementById("rest_btn").innerText = "Отдых (60с)"; } 
    updateNextSetNumber(); 
    loadDayData(); 
}

function updateNextSetNumber() { 
    if (!currentlyExecutingExercise) { document.getElementById("set_num").value = 1; return; } 
    let count = 0; 
    globalHistory.forEach(item => { if(item.ex === currentlyExecutingExercise) { count++; } }); 
    document.getElementById("set_num").value = count + 1; 
}

function deletePlanItem(event, exName) { 
    event.stopPropagation(); 
    const d = document.getElementById("target_date").value; 
    fetch("/delete_plan_item", { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ date: d, ex: exName }) }).then(() => { 
        if(currentlyExecutingExercise === exName) { 
            currentlyExecutingExercise = ""; 
            document.getElementById("active_ex_title").innerText = " (Упражнение не выбрано)"; 
        } 
        loadDayData(); 
    }); 
}

function deleteHistoryItem(event, id) { 
    event.stopPropagation(); 
    fetch("/delete_history_item", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ id: id }) }).then(() => loadDayData()); 
}

function saveCurrentPlanAsTemplate() {
    const tName = prompt("Введите название для этого комплекса (например: Комплекс А, Ноги):");
    if(!tName) return;
    const d = document.getElementById("target_date").value;
    
    fetch("/save_as_template", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({date: d, name: tName.trim()})
    }).then(res=>res.json()).then(data=>{
        if(data.status === "success") {
            alert(`Комплекс "${tName}" сохранен и добавлен в список упражнений!`);
            location.reload();
        } else {
            alert(data.message);
        }
    });
}

function addCustomToBase(){ 
    const n = document.getElementById("exercise_search_input").value.trim(); 
    if(!n){ alert("Введите название нового упражнения в строку поиска, затем нажмите ⭐"); return; } 
    fetch("/add_to_base",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:n})}).then(()=> location.reload()); 
}

function addToDailyPlan(){ 
    const d = document.getElementById("target_date").value, ex = document.getElementById("exercise_search_input").value.trim(); 
    if(!ex){ alert("Выберите или введите упражнение в строку поиска!"); return; } 
    fetch("/add_to_plan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({date:d,ex:ex,sets:3})}).then(()=>{ 
        document.getElementById("exercise_search_input").value = ""; 
        loadDayData(); 
    }); 
}

function startSet(){ 
    if(!currentlyExecutingExercise){ alert("Сначала выберите упражнение из плана дня!"); return; } 
    if(!isExercising){ 
        if(isResting){ 
            clearInterval(timerInterval); 
            isResting = false; 
            document.getElementById("rest_btn").style.background = "#1565c0"; 
            document.getElementById("rest_btn").innerText = "Отдых ("+defaultRestTime+"с)"; 
        } 
        fetch("/start_set",{method:"POST"}).then(()=>{ 
            isExercising = true; 
            exerciseSeconds = 0; 
            document.getElementById("start_btn").style.background = "#ff9100"; 
            document.getElementById("start_btn").innerText = "Секундомер: " + exerciseSeconds + "с"; 
            exerciseInterval = setInterval(()=>{ 
                exerciseSeconds++; 
                document.getElementById("start_btn").innerText = "Секундомер: " + exerciseSeconds + "с"; 
            },1000); 
        }); 
    }else{ stopExerciseTimer(); saveCurrentSet(); } 
}

function stopExerciseTimer(){ 
    if(isExercising){ 
        clearInterval(exerciseInterval); 
        isExercising = false; 
        document.getElementById("start_btn").style.background = "#2e7d32"; 
        document.getElementById("start_btn").innerText = "Старт"; 
    } 
}

function toggleRest(){ 
    if(!currentlyExecutingExercise){ alert("Выберите упражнение из плана!"); return; } 
    if(!isResting){ 
        if(isExercising){ stopExerciseTimer(); saveCurrentSet(); } 
        isResting = true; 
        timeLeft = defaultRestTime; 
        document.getElementById("rest_btn").style.background = "#c62828"; 
        document.getElementById("rest_btn").innerText = "Отдых: " + timeLeft + "c"; 
        timerInterval = setInterval(()=>{ 
            timeLeft--; 
            if(timeLeft > 0){ 
                document.getElementById("rest_btn").innerText = "Отдых: " + timeLeft + "c"; 
            }else{ 
                clearInterval(timerInterval); 
                isResting = false; 
                document.getElementById("rest_btn").style.background = "#1565c0"; 
                document.getElementById("rest_btn").innerText = "Отдых ("+defaultRestTime+"с)"; 
                document.getElementById("start_btn").innerText = "Старт"; 
                playBeep(); 
            } 
        },1000); 
    }else{ 
        clearInterval(timerInterval); 
        isResting = false; 
        document.getElementById("rest_btn").style.background = "#1565c0"; 
        document.getElementById("rest_btn").innerText = "Отдых ("+defaultRestTime+"с)"; 
    } 
}

function saveCurrentSet(){ 
    const d = document.getElementById("target_date").value, w = document.getElementById("weight").value, s = document.getElementById("set_num").value, r = document.getElementById("reps").value; 
    fetch("/save_set",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({date:d,ex:currentlyExecutingExercise,weight:w,setNum:s,reps:r,duration:exerciseSeconds})}).then(()=> { loadDayData(); }); 
}
</script>
</body>
</html>
"""
# Финальная сборка сверхлегкого интерфейса
HTML_CODE = HTML_TEMPLATE.replace("</body>\n</html>", "") + JS_CODE + JS_CODE_2

@app.route('/')
def index():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM exercise_base WHERE is_active = 1 ORDER BY name ASC")
        exercises = [row for row in cursor.fetchall()]
    return render_template_string(HTML_CODE, exercises=exercises)

@app.route('/get_day_data')
def get_day_data():
    target_date = request.args.get('date', time.strftime("%Y-%m-%d"))
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT exercise_name, planned_sets FROM daily_plans WHERE date = ?", (target_date,))
        plan = [{"ex": row, "sets": row} for row in cursor.fetchall()]
        
        cursor.execute("SELECT id, exercise_name, set_num, reps, weight, start_time, duration FROM workout_history WHERE date = ?", (target_date,))
        history = [{"id": row, "ex": row, "setNum": row, "reps": row, "weight": row, "time": row, "duration": row} for row in cursor.fetchall()]
    return jsonify({"plan": plan, "history": history})

@app.route('/get_global_stats')
def get_global_stats():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT date) FROM workout_history WHERE exercise_name != '🧘 Вестибулярная гимнастика'")
        res_days = cursor.fetchone()
        days = res_days if res_days and res_days else 0
        
        cursor.execute("SELECT COUNT(*) FROM workout_history WHERE exercise_name = '🧘 Вестибулярная гимнастика'")
        res_vest = cursor.fetchone()
        vest = res_vest if res_vest and res_vest else 0
        
        cursor.execute("""
            SELECT exercise_name, COUNT(DISTINCT date) as days_cnt 
            FROM workout_history 
            WHERE exercise_name != '🧘 Вестибулярная гимнастика'
            GROUP BY exercise_name 
            ORDER BY days_cnt DESC 
            LIMIT 5
        """)
        top_rows = cursor.fetchall()
        
        top_exercises = []
        for row in top_rows:
            ex_name = row
            days_cnt = row
            
            cursor.execute("SELECT MAX(weight), MAX(duration) FROM workout_history WHERE exercise_name = ?", (ex_name,))
            rec = cursor.fetchone()
            max_w = rec if rec and rec else 0.0
            max_dur = rec if rec and rec else 0
            
            max_r = 0
            if max_w > 0:
                cursor.execute("SELECT MAX(reps) FROM workout_history WHERE exercise_name = ? AND weight = ?", (ex_name, max_w))
                r_row = cursor.fetchone()
                max_r = r_row if r_row and r_row else 0
            
            cursor.execute("""
                SELECT date, MAX(weight), MAX(reps), COUNT(*), MAX(duration)
                FROM workout_history
                WHERE exercise_name = ?
                GROUP BY date
                ORDER BY date DESC
                LIMIT 5
            """, (ex_name,))
            h_rows = cursor.fetchall()
            ex_history = [{"date": h, "w": h, "r": h, "sets": h, "dur": h} for h in h_rows]
            
            top_exercises.append({
                "name": ex_name,
                "days_cnt": days_cnt,
                "max_weight": max_w,
                "max_reps": max_r,
                "max_duration": max_dur,
                "history": ex_history
            })
            
    return jsonify({
        "total_days": days,
        "total_vest": vest,
        "top_exercises": top_exercises
    })

@app.route('/get_single_ex_stat')
def get_single_ex_stat():
    name = request.args.get('name', '')
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT date) FROM workout_history WHERE exercise_name = ?", (name,))
        res_cnt = cursor.fetchone()
        days_cnt = res_cnt if res_cnt and res_cnt else 0
        
        cursor.execute("SELECT MAX(weight), MAX(duration) FROM workout_history WHERE exercise_name = ?", (name,))
        rec = cursor.fetchone()
        max_w = rec if rec and rec else 0.0
        max_dur = rec if rec and rec else 0
        
        max_r = 0
        if max_w > 0:
            cursor.execute("SELECT MAX(reps) FROM workout_history WHERE exercise_name = ? AND weight = ?", (name, max_w))
            r_row = cursor.fetchone()
            max_r = r_row if r_row and r_row else 0
            
        cursor.execute("""
            SELECT date, MAX(weight), MAX(reps), COUNT(*), MAX(duration)
            FROM workout_history
            WHERE exercise_name = ?
            GROUP BY date
            ORDER BY date DESC
        """, (name,))
        h_rows = cursor.fetchall()
        ex_history = [{"date": h, "w": h, "r": h, "sets": h, "dur": h} for h in h_rows]
        
    return jsonify({
        "name": name,
        "days_cnt": days_cnt,
        "max_weight": max_w,
        "max_reps": max_r,
        "max_duration": max_dur,
        "history": ex_history
    })

@app.route('/update_plan_sets', methods=['POST'])
def update_plan_sets():
    data = request.json
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT planned_sets FROM daily_plans WHERE date = ? AND exercise_name = ?", (data["date"], data["ex"]))
        row = cursor.fetchone()
        if row:
            new_sets = max(1, int(row) + int(data["delta"]))
            cursor.execute("UPDATE daily_plans SET planned_sets = ? WHERE date = ? AND exercise_name = ?", (new_sets, data["date"], data["ex"]))
            conn.commit()
    return jsonify({"status": "success"})

@app.route('/save_as_template', methods=['POST'])
def save_as_template():
    data = request.json
    t_name = data["name"].strip()
    date_val = data["date"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT exercise_name, planned_sets FROM daily_plans WHERE date = ?", (date_val,))
        current_plan = cursor.fetchall()
        if not current_plan:
            return jsonify({"status": "error", "message": "План на этот день пуст!"})
        try:
            cursor.execute("INSERT INTO exercise_base (name, is_active) VALUES (?, 1)", (t_name,))
        except sqlite3.IntegrityError:
            cursor.execute("UPDATE exercise_base SET is_active = 1 WHERE name = ?", (t_name,))
        cursor.execute("DELETE FROM templates WHERE template_name = ?", (t_name,))
        for row in current_plan:
            cursor.execute("INSERT INTO templates (template_name, exercise_name, sets) VALUES (?, ?, ?)", (t_name, row, row))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/add_to_base', methods=['POST'])
def add_to_base():
    name = request.json["name"].strip()
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.cursor().execute("INSERT INTO exercise_base (name, is_active) VALUES (?, 1)", (name,))
            conn.commit()
    except sqlite3.IntegrityError:
        with sqlite3.connect(DB_NAME) as conn:
            conn.cursor().execute("UPDATE exercise_base SET is_active = 1 WHERE name = ?", (name,))
            conn.commit()
    return jsonify({"status": "success"})

@app.route('/archive_exercise', methods=['POST'])
def archive_exercise():
    name = request.json["name"].strip()
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("UPDATE exercise_base SET is_active = 0 WHERE name = ?", (name,))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/add_to_plan', methods=['POST'])
def add_to_plan():
    data = request.json
    date_val = data["date"]
    ex_name = data["ex"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT exercise_name, sets FROM templates WHERE template_name = ?", (ex_name,))
        template_items = cursor.fetchall()
        if template_items:
            for row in template_items:
                cursor.execute("SELECT COUNT(*) FROM daily_plans WHERE date = ? AND exercise_name = ?", (date_val, row))
                if cursor.fetchone() == 0:
                    cursor.execute("INSERT INTO daily_plans (date, exercise_name, planned_sets) VALUES (?, ?, ?)", (date_val, row, row))
        else:
            cursor.execute("SELECT COUNT(*) FROM daily_plans WHERE date = ? AND exercise_name = ?", (date_val, ex_name))
            if cursor.fetchone() == 0:
                cursor.execute("INSERT INTO daily_plans (date, exercise_name, planned_sets) VALUES (?, ?, ?)", (date_val, ex_name, int(data["sets"])))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/delete_plan_item', methods=['POST'])
def delete_plan_item():
    data = request.json
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("DELETE FROM daily_plans WHERE date = ? AND exercise_name = ?", (data["date"], data["ex"]))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/delete_history_item', methods=['POST'])
def delete_history_item():
    data = request.json
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("DELETE FROM workout_history WHERE id = ?", (int(data["id"]),))
        conn.commit()
    return jsonify({"status": "success"})

@app.route('/start_set', methods=['POST'])
def start_set():
    current_set_start["time"] = time.strftime("%H:%M:%S")
    return jsonify({"status": "success"})

@app.route('/save_set', methods=['POST'])
def save_set():
    data = request.json
    date_val = data.get("date", time.strftime("%Y-%m-%d"))
    if not current_set_start["time"]: current_set_start["time"] = time.strftime("%H:%M:%S")
    dur = data.get("duration", 0)
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("INSERT INTO workout_history (date, exercise_name, set_num, reps, weight, start_time, duration) VALUES (?, ?, ?, ?, ?, ?, ?)", (date_val, data["ex"], int(data["setNum"]), int(data["reps"]), float(data["weight"]), current_set_start["time"], int(dur)))
        conn.commit()
    current_set_start["time"] = None
    return jsonify({"status": "success"})

# --- ОБНОВЛЕННАЯ СТАБИЛЬНАЯ ОБЕРТКА БЕЗ ВЫЛЕТОВ ---
def start_flask():
    app.run(host='127.0.0.1', port=5000, debug=False)

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.app import mainthread
from jnius import autoclass

class FitnessDiaryApp(App):
    def build(self):
        # Стартуем сервер Flask в изолированном потоке
        threading.Thread(target=start_flask, daemon=True).start()
        
        # Откладываем создание WebView на 2 секунды, чтобы порт точно открылся
        Clock.schedule_once(self.create_webview, 2.0)
        return Widget()

    @mainthread
    def create_webview(self, dt):
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity
            
            WebView = autoclass('android.webkit.WebView')
            WebViewClient = autoclass('android.webkit.WebViewClient')
            
            self.webview = WebView(activity)
            self.webview.getSettings().setJavaScriptEnabled(True)
            self.webview.getSettings().setDomStorageEnabled(True)
            
            # Заставляем ссылки открываться внутри приложения, а не вылетать в браузер
            self.webview.setWebViewClient(WebViewClient())
            self.webview.loadUrl('http://127.0.0')
            
            # Безопасный вывод на главный экран Android
            activity.setContentView(self.webview)
        except Exception as e:
            print(f"Ошибка инициализации WebView: {e}")

if __name__ == '__main__':
    FitnessDiaryApp().run()

