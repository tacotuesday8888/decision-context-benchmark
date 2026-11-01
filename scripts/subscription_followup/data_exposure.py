"""Read-only fingerprints of all known prior prepared/reviewed source records.

No model answers, accounting credentials or environment files are read. Source
candidate/task strings stay in memory; tracked receipts contain hashes/counts.
"""
from __future__ import annotations
from collections import Counter,defaultdict
import hashlib,json,re,unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CANONICAL=ROOT.parent/"Decision Context Benchmark"
PLAN=ROOT.parent/"Decision Context Benchmark Plan"
CHECKOUTS=(("followup",ROOT),("canonical",CANONICAL),("prepared",PLAN))


def sha(body):return hashlib.sha256(body).hexdigest()
def words(value):return re.findall(r"\w+",unicodedata.normalize("NFKC",value).casefold())
def norm(value):return " ".join(words(value))
def grams(value):
    tokens=words(value)
    return set(zip(tokens,tokens[1:],tokens[2:]))


def documents(value):
    """Substantive released JSON objects only; never create classifier inputs."""
    try:
        parsed=json.loads(value)
    except (ValueError,TypeError):
        if not isinstance(value,str) or len(value)>200000 or not value.lstrip().startswith("- "):return set()
        try:
            import yaml
        except ImportError:return set()
        try:
            parsed=yaml.safe_load(value)
        except (ValueError,TypeError,yaml.YAMLError):return set()
    result=set()
    def walk(obj):
        if isinstance(obj,list):
            for child in obj:walk(child)
        elif isinstance(obj,dict):
            text_fields=[v for k,v in obj.items() if k.lower() in {"body","description","content","text"} and isinstance(v,str) and len(v.strip())>=60]
            event={k.rstrip("_"):v for k,v in obj.items() if k.rstrip("_") in {"id","title","description","start_time","end_time","location","participants"}}
            if {"id","title","start_time","end_time"} <= set(event):
                # Same substantive published calendar entity across JSON/YAML
                # renderings; full classifier candidates remain byte-identical.
                rendered=json.dumps(event,sort_keys=True,ensure_ascii=False,default=str)
                rendered=re.sub(r"(\d{4}-\d{2}-\d{2})T(\d{2}:)",r"\1 \2",rendered)
                result.add("calendar:"+sha(norm(rendered).encode()))
            if text_fields and any(k.lower() in {"id","id_","event_id","subject","title","sender"} for k in obj):
                result.add(sha(norm(json.dumps(obj,sort_keys=True,ensure_ascii=False,default=str)).encode()))
            for child in obj.values():
                if isinstance(child,(dict,list)):walk(child)
    walk(parsed)
    return result


def historical_paths():
    relative={"data/raw/pilot.jsonl","data/pilot.jsonl","data/expanded-v2/collection.jsonl","data/raw/expanded-v2/pre-query-audit-collection.jsonl",
        "data/raw/extension-v3/prepared-collection-v1.jsonl","data/raw/extension-v3/agentdojo-clean-replay.jsonl",
        "data/raw/controls-v4/prepared-collection-v1.jsonl","data/raw/controls-v4/tasktracker-reconstructed-v1.jsonl",
        "data/raw/controls-v4/tasktracker-advbench-reconstructed-v1.jsonl","data/raw/controls-v4/tasktracker-clean-reconstructed-v1.jsonl",
        "data/raw/controls-v4/aib-prepared-v1.jsonl","data/raw/study-v5/prepared-review.jsonl",
        "data/raw/study-v5/grouped-review-v2.jsonl","data/raw/study-v5/scope-pairs.jsonl",
        "data/raw/study-v5/review-packet.jsonl","data/raw/study-v5/scope-review-packet.jsonl",
        "data/raw/study-v6/prepared.jsonl","data/raw/study-v6/browse-train-selected.jsonl",
        "data/raw/study-v6/nvidia-prepared.jsonl","data/raw/study-v6/review-packet.jsonl",
        "data/raw/study-v7/main-selected.jsonl","data/raw/study-v7/external-selected.jsonl",
        "data/raw/study-v7/external-selected-v2.jsonl","data/raw/study-v7/external-selected-v3.jsonl",
        "results/extension-v3/collection-manifest-v1.jsonl","results/controls-v4/collection-manifest-v1.jsonl",
        "results/controls-v4/exposure-register-v1.jsonl","results/controls-v4/tau-trajectory-inventory-v1.jsonl"}
    relative.update("data/raw/source-discovery/"+name for name in ("aib-review-v1.jsonl","aib-cases.jsonl","nexus-v1.jsonl","nexus-v2.jsonl",
        "Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1-train.jsonl","spml-review-v1.jsonl",
        "blinded-review-v1.jsonl","blinded-mapping-v1.jsonl","aspi-data-workspace.jsonl","aspi-data-banking.jsonl",
        "aspi-data-slack.jsonl","aspi-data-travel.jsonl"))
    return sorted({(base/name).resolve() for label,base in CHECKOUTS for name in relative if (base/name).is_file()})


def indexed_candidate_messages(payload):
    """Retain every prior indexed candidate, not merely the first tool message."""
    messages=payload.get("source_conversation_inputs",[])
    indexed={m.get("original_index",i):m for i,m in enumerate(messages)}
    if len(indexed)!=len(messages):raise ValueError("Historical original message indexes are duplicated")
    indexes=payload.get("candidate_message_indexes")
    if indexes is None:
        indexes=[m.get("original_index",i) for i,m in enumerate(messages) if m.get("role")=="tool_result"]
    if not isinstance(indexes,list):raise ValueError("Historical candidate indexes must be a list")
    result=[]
    for i in indexes:
        if type(i) is not int or i not in indexed or not isinstance(indexed[i].get("content"),str):
            raise ValueError("Historical indexed candidate cannot be reconstructed")
        result.append((i,indexed[i]["content"]))
    return result


def build_history():
    rows=[];receipts=[];task_ids=set();raw_hashes=defaultdict(set);document_hashes=defaultdict(set)
    for path in historical_paths():
        label,base=next((label,base) for label,base in CHECKOUTS if base in path.parents)
        count=0;text_count=0
        for line in path.open():
            row=json.loads(line);count+=1
            metadata={k:row.get(k) for k in ("id","source","groups","group","group_id","task_group","task")}
            serialized=json.dumps(metadata,sort_keys=True)
            task_ids.update("agentdojo:"+suite+":"+task for suite,task in re.findall(r"(workspace|travel|banking|slack)[:/](user_task_\d+)",serialized))
            if row.get("suite") in {"workspace","travel","banking","slack"} and isinstance(row.get("user_task_id"),str):
                task_ids.add("agentdojo:"+row["suite"]+":"+row["user_task_id"])
            task_ids.update(re.findall(r"tau-bench:(?:retail|airline):\d+",serialized))
            candidate=next((row[k] for k in ("candidate","content_markdown","text") if isinstance(row.get(k),str)),"")
            task=next((row[k] for k in ("trusted_task","benign_task","task","original_prompt","request") if isinstance(row.get(k),str)),"")
            payload=row.get("detector_payload") or {}
            if not candidate:
                candidate=payload.get("submitted_user_prompt") or next((m.get("content","") for m in payload.get("source_conversation_inputs",[]) if m.get("role")=="tool_result"),"")
            if not task:task=payload.get("actual_user_task") or ""
            if not candidate and row.get("structured_plan"):
                candidate=json.dumps(row["structured_plan"],sort_keys=True,ensure_ascii=False)
            if not candidate and isinstance(row.get("conversation"),list):
                candidate="\n".join(m.get("content","") for m in row["conversation"] if m.get("role")=="tool" and isinstance(m.get("content"),str))
                task=task or "\n".join(m.get("content","") for m in row["conversation"] if m.get("role")=="user" and isinstance(m.get("content"),str))
            if row.get("responses_create_params"):
                inputs=row["responses_create_params"].get("input",[])
                if isinstance(inputs,list):
                    task=task or "\n".join(m.get("content","") for m in inputs if isinstance(m,dict) and m.get("role")=="user" and isinstance(m.get("content"),str))
                injection=row.get("injection",{})
                candidate=candidate or injection.get("injection_text","")

            identity=str(path.relative_to(base))+":"+str(row.get("id",count))
            for field in ("candidate_sha256","text_sha256"):
                if isinstance(row.get(field),str):raw_hashes[row[field]].add(identity)
            if candidate:
                text_count+=1;raw_hashes[sha(candidate.encode())].add(identity)
                for fingerprint in documents(candidate):document_hashes[fingerprint].add(identity)
            if candidate or task:rows.append({"id":identity,"candidate":candidate,"task":task})
            seen={candidate}
            for index,text in indexed_candidate_messages(payload):
                if not text or text in seen:continue
                seen.add(text);text_count+=1;constituent=identity+":candidate_message:"+str(index)
                raw_hashes[sha(text.encode())].add(constituent)
                for fingerprint in documents(text):document_hashes[fingerprint].add(constituent)
                rows.append({"id":constituent,"candidate":text,"task":task})
        receipts.append({"checkout":label,"path":str(path.relative_to(base)),
            "sha256":sha(path.read_bytes()),"rows":count,"candidate_text_rows":text_count})
    return {"rows":rows,"receipts":receipts,"task_ids":task_ids,"raw_hashes":raw_hashes,"document_hashes":document_hashes}


def screen(task,candidates,history):
    """Close historical exact/near task, candidate and substantive document edges."""
    hits=[];task_norm=norm(task);task_grams=grams(task)
    normalized=[norm(text) for text in candidates];candidate_grams=[grams(text) for text in candidates]
    for i,text in enumerate(candidates):
        for match in sorted(history["raw_hashes"].get(sha(text.encode()),set())):
            hits.append({"axis":"candidate","kind":"byte_exact","arm":i,"historical_id":match})
        for fingerprint in documents(text):
            for match in sorted(history["document_hashes"].get(fingerprint,set())):
                hits.append({"axis":"document","kind":"substantive_json_object_exact","arm":i,"historical_id":match})
    if "lexical_index" not in history:
        index={axis:{"unique":{},"postings":defaultdict(set)} for axis in ("task","candidate")}
        for previous in history["rows"]:
            for axis in index:
                value=norm(previous[axis])
                if not value:continue
                unique=index[axis]["unique"]
                if value not in unique:
                    tokens=value.split();g=set(zip(tokens,tokens[1:],tokens[2:]))
                    unique[value]={"grams":g,"ids":[]}
                    for gram in g:index[axis]["postings"][gram].add(value)
                unique[value]["ids"].append(previous["id"])
        history["lexical_index"]=index
    for axis,current_norm,current_grams,threshold in [("task",task_norm,task_grams,.5)]+[("candidate",n,g,.8) for n,g in zip(normalized,candidate_grams)]:
        if not current_norm:continue
        index=history["lexical_index"][axis]
        exact=index["unique"].get(current_norm)
        if exact:
            hits.extend({"axis":axis,"kind":"normalized_exact","historical_id":identity} for identity in exact["ids"])
        possible=set()
        for gram in current_grams:possible.update(index["postings"].get(gram,set()))
        for other in possible:
            if other==current_norm:continue
            record=index["unique"][other];other_grams=record["grams"]
            if min(len(current_grams),len(other_grams))<5:continue
            # Jaccard cannot reach threshold outside this length ratio.
            if min(len(current_grams),len(other_grams))/max(len(current_grams),len(other_grams))<threshold:continue
            overlap=len(current_grams&other_grams);union=len(current_grams|other_grams)
            if union and overlap/union>=threshold:
                hits.extend({"axis":axis,"kind":"three_word_jaccard","threshold":threshold,"jaccard":overlap/union,"historical_id":identity} for identity in record["ids"])
    return hits
