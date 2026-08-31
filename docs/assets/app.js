(function(){
"use strict";
function q(s,r){return (r||document).querySelector(s)}
function qa(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))}
function cap(s){return s.charAt(0).toUpperCase()+s.slice(1)}
function esc(s){return String(s).replace(/[&<>'"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]})}

var phases={
 define:{badge:"DEFINE",progress:24,title:"Define the problem precisely",kicker:"Problem framing",pt:"What is happening?",copy:"Change requests are taking too long to move from intake to decision, causing repeated stakeholder escalation and missed downstream planning dates.",ev:"Supported",evc:"supported",signals:["Cycle time varies widely from request to request","Status requests are frequent because ownership is unclear","Rework occurs when intake information is incomplete"],nt:"Make the operational definition measurable.",nc:"Confirm where cycle time starts and stops, which request types are in scope, and who owns the decision point.",why:"A stable definition prevents later analysis from mixing different processes.",bars:{supported:72,inferred:18,missing:10},out:["Problem statement","CTQs","SIPOC","Scope","Stakeholders","Baseline context"]},
 measure:{badge:"MEASURE",progress:43,title:"Turn symptoms into trustworthy measures",kicker:"Baseline & data plan",pt:"What should be measured?",copy:"Current baseline signals include 18-day average cycle time, 27% rework, and six escalations per month. Their definitions and collection method still need verification.",ev:"Supported + missing",evc:"missing",signals:["Define request-level cycle-time timestamps","Segment rework by missing-information reason","Track queue time separately from active review time"],nt:"Validate the measurement system before optimizing it.",nc:"Check whether timestamps, request categories, and rework labels are captured consistently enough to support conclusions.",why:"Poor measurement can create a precise-looking answer to the wrong question.",bars:{supported:54,inferred:16,missing:30},out:["Operational definitions","Data plan","Baseline","Sampling approach","MSA check","Data-quality gaps"]},
 analyze:{badge:"ANALYZE",progress:63,title:"Test causes instead of promoting guesses",kicker:"Root-cause analysis",pt:"What is driving the delay?",copy:"Unclear ownership and incomplete intake information are plausible drivers, but the available project description does not establish their quantitative contribution to cycle time.",ev:"Inferred",evc:"inferred",signals:["Compare cycle time by request completeness","Map handoffs and waiting time","Test whether owner ambiguity predicts escalation or rework"],nt:"Collect evidence at the handoff points.",nc:"Use timestamped request data and structured reason codes to test which bottlenecks explain the largest share of delay and rework.",why:"A cause is useful only when evidence can distinguish it from a plausible story.",bars:{supported:45,inferred:38,missing:17},out:["Root-cause hypotheses","Fishbone / 5 Whys","Pareto view","Hypothesis tests","FMEA","Validated causes"]},
 improve:{badge:"IMPROVE",progress:82,title:"Design changes against validated causes",kicker:"Countermeasures",pt:"What should change first?",copy:"Potential improvements include completeness gates, explicit decision ownership, and review-service expectations. They should be prioritized after root causes are validated.",ev:"Inferred",evc:"inferred",signals:["Pilot an intake completeness check","Assign one accountable decision owner","Test a visible review queue with aging limits"],nt:"Pilot the smallest change that can disprove the hypothesis.",nc:"Define a target, owner, trial window, and success metric before changing the wider process.",why:"Small controlled trials reduce implementation cost and make effects easier to attribute.",bars:{supported:36,inferred:50,missing:14},out:["Solution options","Prioritization","Pilot plan","Owner matrix","Expected benefit","Risk review"]},
 control:{badge:"CONTROL",progress:100,title:"Keep the gain visible after the project ends",kicker:"Sustainment",pt:"How will the process stay in control?",copy:"A control plan should define the small set of measures, owners, review cadence, and escalation triggers needed to detect regression early.",ev:"Inferred",evc:"inferred",signals:["Monitor cycle-time distribution, not only the average","Track rework and queue aging","Define trigger thresholds and accountable response owners"],nt:"Make ownership and reaction rules explicit.",nc:"A metric without a decision rule is only reporting. Tie each control metric to a review cadence and response action.",why:"Control closes the loop between measurement and operational response.",bars:{supported:40,inferred:44,missing:16},out:["Control plan","SPC / KPI view","Reaction plan","Ownership","Review cadence","Handover"]}
};

var tools={
 spc:{n:"01 / STABILITY",name:"SPC control chart",d:"Use control charts to distinguish common-cause variation from signals that suggest the process changed.",use:"Measurements arrive in time order and you want to understand process stability.",watch:"Do not interpret specification limits as control limits.",path:"analytics/spc.py"},
 capability:{n:"02 / CAPABILITY",name:"Process capability",d:"Compare process variation and centering against specification limits using Cp/Cpk or Pp/Ppk as appropriate.",use:"The process is sufficiently stable and specification limits are meaningful.",watch:"Capability indices are misleading when the process is unstable or assumptions are violated.",path:"analytics/capability.py"},
 hypothesis:{n:"03 / COMPARISON",name:"Hypothesis testing",d:"Choose a test that matches the outcome type, number of groups, pairing, and distribution assumptions.",use:"You need to evaluate whether an observed group difference is larger than expected from sampling variation.",watch:"Statistical significance does not establish practical importance or causality.",path:"analytics/hypothesis_testing.py"},
 regression:{n:"04 / RELATIONSHIP",name:"Regression",d:"Model relationships between an outcome and one or more explanatory variables to quantify patterns and residual uncertainty.",use:"You want to understand how measured inputs relate to a continuous outcome.",watch:"Association can be confounded; inspect residuals and model assumptions before interpretation.",path:"analytics/regression.py"},
 msa:{n:"05 / MEASUREMENT",name:"MSA / Gauge R&R",d:"Estimate how much observed variation comes from the measurement system rather than the process itself.",use:"Different appraisers, instruments, or repeated measurements may be introducing material variation.",watch:"A capable process analysis depends on a measurement system that is fit for the intended decision.",path:"analytics/msa.py"},
 fmea:{n:"06 / RISK",name:"FMEA",d:"Structure failure modes, effects, causes, and controls so risk-reduction work can be prioritized transparently.",use:"You need a systematic view of where a process or proposed change can fail.",watch:"RPN alone can hide severe risks; review severity and control effectiveness explicitly.",path:"analytics/fmea.py"}
};

var arch={
 intake:{layer:"INPUT LAYER",name:"Project intake",d:"Collects project context and converts it into the explicit ProjectInput contract used by the assessment engine.",r:"Capture context without claiming evidence that was not supplied.",p:"ui/forms.py · src/models.py · templates/",b:"UI collection should remain separate from assessment reasoning."},
 engine:{layer:"ORCHESTRATION",name:"Assessment engine",d:"Coordinates assessment modes and transforms validated input contracts into structured result objects.",r:"Choose and run assessment logic while keeping the result schema stable.",p:"src/engine.py · src/phases/",b:"Orchestration should not own presentation or persistence concerns."},
 evidence:{layer:"REASONING GUARDRAIL",name:"Evidence discipline",d:"Carries supported, inferred, and missing states through assessment output so hypotheses remain visibly distinct from supplied facts.",r:"Prevent AI-generated plausibility from becoming implied evidence.",p:"src/models.py · docs/evidence-discipline.md",b:"Evidence labels must be preserved through every renderer and UI surface."},
 analytics:{layer:"QUANTITATIVE WORKBENCH",name:"Analytics",d:"Provides focused statistical tools for capability, MSA, hypothesis testing, SPC, FMEA, regression, DOE, and benefits analysis.",r:"Make quantitative methods available without burying their assumptions and limitations.",p:"analytics/ · ui/analytics_workbench.py",b:"Statistical calculations should remain testable independently of the UI."},
 renderers:{layer:"OUTPUT LAYER",name:"Renderers & exports",d:"Converts structured assessment results into shareable Markdown, HTML, PDF, Word, and Excel artifacts.",r:"Preserve meaning and evidence states across formats.",p:"src/renderers.py · src/exporters.py",b:"Renderers format results; they should not invent assessment content."},
 ui:{layer:"INTERACTION LAYER",name:"User interfaces",d:"The Streamlit runtime supports real project work, while GitHub Pages provides public orientation and a deterministic browser demo.",r:"Expose the same underlying concepts at the right level of detail for each audience.",p:"app.py · ui/ · docs/index.html",b:"The static site must never imply that browser-only demonstrations are running the Python/AI backend."}
};

var concernTool={
 "cycle-time":["SPC + process map","Establish the time-ordered baseline and identify where waiting accumulates."],
 quality:["Pareto + FMEA","Separate dominant defect or rework categories, then prioritize failure risks."],
 variation:["SPC control chart","Determine whether variation is stable before treating every fluctuation as a special cause."],
 cost:["COPQ / benefits","Quantify where poor quality and delay consume money before ranking improvement options."],
 measurement:["MSA / Gauge R&R","Check whether the measurement system is trustworthy enough for downstream analysis."]
};
var measures={
 "cycle-time":["End-to-end cycle time","Queue / waiting time by handoff","Rework rate and number of loops"],
 quality:["Defect or rework rate","Defect category / Pareto share","First-pass yield"],
 variation:["Time-ordered outcome measure","Center line and control limits","Special-cause signals"],
 cost:["Cost of poor quality","Cost per case / transaction","Avoidable rework and delay cost"],
 measurement:["Repeatability","Reproducibility","Measurement-system contribution to total variation"]
};

function renderPhase(key){
 var p=phases[key]; if(!p)return;
 qa(".phase-nav button").forEach(function(b){b.classList.toggle("selected",b.getAttribute("data-phase")===key)});
 q("#progress-label").textContent=p.progress+"%";q("#progress-bar").style.width=p.progress+"%";
 q("#phase-title").textContent=p.title;q("#phase-badge").textContent=p.badge;q("#phase-kicker").textContent=p.kicker;
 q("#phase-primary-title").textContent=p.pt;q("#phase-primary-copy").textContent=p.copy;
 var e=q("#phase-evidence");e.textContent=p.ev;e.className="tag "+p.evc;
 q("#phase-signals").innerHTML=p.signals.map(function(x){return '<div class="signal">'+esc(x)+"</div>"}).join("");
 q("#phase-next-title").textContent=p.nt;q("#phase-next-copy").textContent=p.nc;q("#phase-why").textContent=p.why;
 q("#evidence-caption").textContent=cap(key)+" view";
 q("#evidence-bars").innerHTML=Object.keys(p.bars).map(function(k){return '<div class="bar-row '+k+'"><span>'+cap(k)+'</span><div class="bar"><i style="width:'+p.bars[k]+'%"></i></div><b>'+p.bars[k]+"</b></div>"}).join("");
 q("#phase-deliverables").innerHTML=p.out.map(function(x){return "<li>"+esc(x)+"</li>"}).join("");
}
function renderTool(key){
 var t=tools[key]; if(!t)return;
 qa(".questions button").forEach(function(b){b.classList.toggle("selected",b.getAttribute("data-tool")===key)});
 q("#tool-number").textContent=t.n;q("#tool-name").textContent=t.name;q("#tool-description").textContent=t.d;
 q("#tool-use").textContent=t.use;q("#tool-watch").textContent=t.watch;q("#tool-path").textContent=t.path;
}
function renderArch(key){
 var a=arch[key];if(!a)return;
 qa(".node").forEach(function(b){b.classList.toggle("selected",b.getAttribute("data-node")===key)});
 q("#arch-layer").textContent=a.layer;q("#arch-name").textContent=a.name;q("#arch-description").textContent=a.d;
 q("#arch-responsibility").textContent=a.r;q("#arch-paths").textContent=a.p;q("#arch-boundary").textContent=a.b;
}
function starter(problem,concern,audience){
 var s=problem.replace(/\s+/g," ").trim(), labels={pm:"PM",quality:"quality lead",engineer:"engineer",manager:"manager",executive:"executive"};
 if(!s){q("#brief-title").textContent="Add a process problem to begin";return}
 q("#brief-title").textContent="Starter view for "+(labels[audience]||"review");
 q("#brief-problem").textContent=s.length>330?s.slice(0,327).trim()+"…":s;
 q("#brief-measures").innerHTML=measures[concern].map(function(x){return "<li>"+esc(x)+"</li>"}).join("");
 var gaps=["Operational definition and scope","Baseline period and sample size","Data source and collection reliability","Named owner for the outcome"];
 if(!/\d/.test(s))gaps.unshift("A numeric baseline or current-state measure");
 if(!/(owner|responsib|accountab|team|role)/i.test(s))gaps.push("Decision or process ownership");
 q("#brief-gaps").innerHTML=gaps.slice(0,4).map(function(x){return "<li>"+esc(x)+"</li>"}).join("");
 q("#brief-tool").textContent=concernTool[concern][0];q("#brief-tool-reason").textContent=concernTool[concern][1];
}
qa(".phase-nav button").forEach(function(b){b.addEventListener("click",function(){renderPhase(b.getAttribute("data-phase"))})});
qa(".questions button").forEach(function(b){b.addEventListener("click",function(){renderTool(b.getAttribute("data-tool"))})});
qa(".node").forEach(function(b){b.addEventListener("click",function(){renderArch(b.getAttribute("data-node"))})});
var input=q("#problem-input");
input.addEventListener("input",function(){q("#char-count").textContent=input.value.length+" / 1200"});
q("#load-sample").addEventListener("click",function(){
 input.value="Supplier change requests are taking too long to move from intake to decision. Cycle time varies widely, teams repeatedly ask for status because ownership is unclear, and 27% of requests require rework when information is incomplete.";
 q("#char-count").textContent=input.value.length+" / 1200";q("#concern-input").value="cycle-time";
 starter(input.value,q("#concern-input").value,q("#audience-input").value);
});
q("#intake-form").addEventListener("submit",function(e){e.preventDefault();starter(input.value,q("#concern-input").value,q("#audience-input").value)});
var stored=localStorage.getItem("lean-ai-theme"),preferred=window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";
document.documentElement.setAttribute("data-theme",stored||preferred);
q("#theme-toggle").addEventListener("click",function(){var next=document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";document.documentElement.setAttribute("data-theme",next);localStorage.setItem("lean-ai-theme",next)});
renderPhase("define");renderTool("spc");renderArch("intake");
})();