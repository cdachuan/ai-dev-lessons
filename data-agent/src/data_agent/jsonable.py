# -*- coding: utf-8 -*-
"""铁律1：所有工具返回值必须过 _to_jsonable，否则 json.dumps 必炸。"""
import numpy as np
import pandas as pd


def _to_jsonable(obj):
    """递归把 pandas/numpy 对象转成 JSON 可序列化结构。"""
    if obj is None or isinstance(obj, (bool, str, int, float)):
        # numpy 标量转 python 标量
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            v = float(obj)
            return v if np.isfinite(v) else None
        return obj
    if isinstance(obj, (np.bool_, np.integer, np.floating)):
        return _to_jsonable(obj.item())
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        if isinstance(obj, np.ndarray):
            obj = obj.tolist()
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, pd.Series):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, pd.DataFrame):
        return {"__type__": "dataframe", "records": obj.to_dict("records")}
    import datetime as _dt
    if isinstance(obj, (_dt.datetime, _dt.date)):
        return obj.isoformat()
    return str(obj)  # 兜底：其他对象转字符串
