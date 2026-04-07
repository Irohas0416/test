import time, json, tracemalloc
from contextlib import contextmanager
from datetime import datetime

class PerfTracker:
    def __init__(self, log_file="performance/logs/perf_log.json"):
        self.log_file = log_file
        self.records = []

    def _try_get_process_metrics(self):
        """
        Best-effort process metrics (system-level, not just Python allocations).
        Returns dict or None if psutil is unavailable.
        """
        try:
            import psutil  # type: ignore
            p = psutil.Process()
            mi = p.memory_info()
            return {
                "rss_mb": round(mi.rss / 1024 / 1024, 2),
                "vms_mb": round(mi.vms / 1024 / 1024, 2),
                "num_threads": getattr(p, "num_threads", lambda: None)(),
            }
        except Exception:
            return None

    @contextmanager
    def stage(self, name, **metadata):
        tracemalloc.start()
        t0 = time.perf_counter()
        cpu0 = time.process_time()
        proc0 = self._try_get_process_metrics()
        record = {"stage": name, "start": datetime.now().isoformat(), "status": "ok", **metadata}
        try:
            yield record
        except Exception as e:
            record["status"] = "error"
            record["error_type"] = type(e).__name__
            record["error_message"] = str(e)
            raise
        finally:
            elapsed = time.perf_counter() - t0
            cpu_elapsed = time.process_time() - cpu0
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            proc1 = self._try_get_process_metrics()
            record.update({
                "elapsed_sec": round(elapsed, 3),
                # Python-level allocations (tracemalloc)
                "py_peak_alloc_mb": round(peak / 1024 / 1024, 2),
                "py_current_alloc_mb": round(current / 1024 / 1024, 2),
                # CPU
                "cpu_time_sec": round(cpu_elapsed, 3),
            })

            # System-level memory (RSS/VMS) if available
            if proc0 and proc1:
                record.update({
                    "rss_mb_start": proc0.get("rss_mb"),
                    "rss_mb_end": proc1.get("rss_mb"),
                    "rss_mb_delta": round((proc1.get("rss_mb") or 0) - (proc0.get("rss_mb") or 0), 2),
                    "vms_mb_start": proc0.get("vms_mb"),
                    "vms_mb_end": proc1.get("vms_mb"),
                    "num_threads_start": proc0.get("num_threads"),
                    "num_threads_end": proc1.get("num_threads"),
                })

            self.records.append(record)
            msg = f"[PERF] {name}: {elapsed:.2f}s, cpu={cpu_elapsed:.2f}s, py_peak={peak/1024/1024:.1f}MB"
            if proc1 and proc1.get("rss_mb") is not None:
                msg += f", rss_end={proc1['rss_mb']:.1f}MB"
            print(msg)

    def log_api_call(self, model, input_tokens, output_tokens):
        # Gemini 2.5 Flash pricing as of late 2025: ~$0.075/$0.30 per 1M tokens
        cost = (input_tokens * 0.075 + output_tokens * 0.30) / 1_000_000
        self.records.append({
            "type": "api_call",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "ts": datetime.now().isoformat(),
        })

    def save(self):
        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        with open(self.log_file, "w") as f:
            json.dump(self.records, f, indent=2)
        print(f"[PERF] Saved {len(self.records)} records to {self.log_file}")

    def summary(self):
        stages = [r for r in self.records if "stage" in r]
        total_time = sum(r["elapsed_sec"] for r in stages)
        total_cpu = sum(r.get("cpu_time_sec", 0) for r in stages)

        rss_ends = [r.get("rss_mb_end") for r in stages if r.get("rss_mb_end") is not None]
        py_peaks = [r.get("py_peak_alloc_mb") for r in stages if r.get("py_peak_alloc_mb") is not None]
        return {
            "total_time_sec": round(total_time, 2),
            "total_cpu_time_sec": round(total_cpu, 2),
            "max_rss_mb_end": max(rss_ends) if rss_ends else None,
            "max_py_peak_alloc_mb": max(py_peaks) if py_peaks else None,
            "stages": stages,
        }