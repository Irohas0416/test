import argparse
import json
import os
import sys

from rdflib import Graph
from rdflib.namespace import OWL, RDFS, XSD

from performance.performance_test import PerfTracker
from mapping.map_stations import map_stations
from mapping.utils import LPT, SCHEMA


def _count_csv_rows(path: str) -> int | None:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            n = sum(1 for _ in f) - 1  # minus header
            return max(n, 0)
    except Exception:
        return None


def run_pipeline(
    pdf_path: str = "data/WTT/picadilly.pdf",
    extracted_csv_path: str | None = None,
    ontology_path: str = "ontology/KNE_ontology_v03.ttl",
    output_ttl_path: str = "data/output/knowledge_graph.ttl",
    parallel_extract: bool = False,
    schema: str = "StationCSVRow",
    mode: str = "both",
    allow_api: bool = False,
):

    if extracted_csv_path is None:
        stem = os.path.splitext(os.path.basename(pdf_path))[0] or "extracted"
        extracted_csv_path = os.path.join("data", "intermediate", f"{stem}.csv")

    os.makedirs(os.path.dirname(extracted_csv_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_ttl_path), exist_ok=True)

    tracker = PerfTracker()
    try:
        # extract PDF to CSV (optional). Default: do NOT call API; reuse CSV.
        if mode in ("both", "extract"):
            with tracker.stage("extract_stations", input_file=pdf_path, output_file=extracted_csv_path) as rec:
                fallback_csv = "data/stations.csv"

                if not allow_api:
                    if os.path.exists(extracted_csv_path):
                        rec["skipped"] = True
                        rec["cache_hit"] = True
                        rec["skip_reason"] = "allow_api_false__use_existing_intermediate_csv"
                    elif os.path.exists(fallback_csv):
                        extracted_csv_path = fallback_csv
                        rec["skipped"] = True
                        rec["cache_hit"] = True
                        rec["skip_reason"] = "allow_api_false__use_fallback_repo_csv"
                        rec["output_file"] = extracted_csv_path
                    else:
                        raise FileNotFoundError(
                            f"allow_api=False and no CSV  found {extracted_csv_path}"
                        )
                else:
                    if not os.path.exists(pdf_path):
                        raise FileNotFoundError(f"cannot find pdf: {pdf_path}")

                    if os.path.exists(extracted_csv_path):
                        try:
                            os.remove(extracted_csv_path)
                            rec["deleted_cached_output"] = True
                        except Exception as e:
                            rec["deleted_cached_output"] = False
                            rec["delete_error"] = str(e)

                    from rag import gemini_extractor  # lazy import

                    args = argparse.Namespace(
                        input=pdf_path,
                        output=extracted_csv_path,
                        schema=schema,
                        append=False,
                        parallel=parallel_extract,
                    )
                    gemini_extractor.main(args)

                    if not os.path.exists(extracted_csv_path):
                        raise RuntimeError(f"no csv file generated: {extracted_csv_path}")

                if os.path.exists(extracted_csv_path):
                    rec["output_file_bytes"] = os.path.getsize(extracted_csv_path)
                    rec["output_rows"] = _count_csv_rows(extracted_csv_path)

        # mapping CSV → TTL (optional)
        if mode in ("both", "map"):
            # If running mapping without extraction, fallback to repo csv when intermediate csv missing.
            if not os.path.exists(extracted_csv_path):
                fallback_csv = "data/stations.csv"
                if os.path.exists(fallback_csv):
                    extracted_csv_path = fallback_csv

            with tracker.stage("map_to_ttl", input_file=extracted_csv_path, output_file=output_ttl_path) as rec:
                if not os.path.exists(extracted_csv_path):
                    raise FileNotFoundError(f"cannot find csv: {extracted_csv_path}")
                if not os.path.exists(ontology_path):
                    raise FileNotFoundError(f"cannot find file:{ontology_path}")

                g = Graph()
                g.parse(ontology_path, format="turtle")
                base_triples = len(g)

                g.bind("lpt", LPT)
                g.bind("schema", SCHEMA)
                g.bind("owl", OWL)
                g.bind("rdfs", RDFS)
                g.bind("xsd", XSD)

                rec["stations_mapped"] = map_stations(g, extracted_csv_path)
                rec["triples_before"] = base_triples
                rec["triples_after"] = len(g)
                rec["triples_added"] = len(g) - base_triples

                g.serialize(destination=output_ttl_path, format="turtle")
                if os.path.exists(output_ttl_path):
                    rec["output_file_bytes"] = os.path.getsize(output_ttl_path)
    finally:
        tracker.save()
        print(json.dumps(tracker.summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run KG pipeline with performance evaluation.")
    parser.add_argument("--pdf", default="data/WTT/picadilly.pdf", help="PDF path to extract from.")
    parser.add_argument("--schema", default="StationCSVRow", help="Schema name used by gemini_extractor (e.g., StationCSVRow).")
    parser.add_argument("--csv_out", default=None, help="Output CSV path (default derived from PDF name).")
    parser.add_argument("--ontology", default="ontology/KNE_ontology_v03.ttl", help="Base ontology TTL path.")
    parser.add_argument("--ttl_out", default="data/output/knowledge_graph.ttl", help="Output TTL path.")
    parser.add_argument("--parallel", action="store_true", help="Enable parallel extraction (dual API keys).")
    parser.add_argument("--mode", choices=["extract", "map", "both"], default="both", help="Run only extraction, only mapping, or both.")
    parser.add_argument("--allow_api", action="store_true", help="Allow calling Gemini API for PDF extraction (default off).")
    args = parser.parse_args()

    run_pipeline(
        pdf_path=args.pdf,
        extracted_csv_path=args.csv_out,
        ontology_path=args.ontology,
        output_ttl_path=args.ttl_out,
        parallel_extract=args.parallel,
        schema=args.schema,
        mode=args.mode,
        allow_api=args.allow_api,
    )