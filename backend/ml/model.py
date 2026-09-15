"""
ML Anomaly Detection Module
Isolation Forest + Rule-based detection for network traffic anomalies.
"""
import asyncio
import logging
import time
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

import numpy as np
import joblib

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, roc_auc_score
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. ML features disabled.")

try:
    import onnx
    import onnxmltools
    from skl2onnx import convert_sklearn
    from skl2onnx.common.data_types import FloatTensorType
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("ONNX tools not available. Model export disabled.")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    logging.warning("LightGBM not available. Using RandomForest as fallback.")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available. Real-time streaming disabled.")


# Feature columns for the ML model
FEATURE_COLUMNS = [
    "duration_ms",
    "packets_fwd", "packets_bwd",
    "bytes_fwd", "bytes_bwd",
    "iat_fwd_mean", "iat_fwd_std",
    "iat_bwd_mean", "iat_bwd_std",
    "pkt_len_fwd_mean", "pkt_len_fwd_std",
    "pkt_len_bwd_mean", "pkt_len_bwd_std",
    "tcp_syn_fwd", "tcp_ack_fwd", "tcp_fin_fwd", "tcp_rst_fwd", "tcp_psh_fwd",
    "tcp_syn_bwd", "tcp_ack_bwd", "tcp_fin_bwd", "tcp_rst_bwd", "tcp_psh_bwd",
    "payload_entropy_fwd_mean", "payload_entropy_bwd_mean",
    "protocol_encoded",
    "src_port_category", "dst_port_category"
]

ATTACK_LABELS = [
    "BENIGN",
    "PORT_SCAN",
    "DDoS",
    "BRUTE_FORCE",
    "C2_BEACONING",
    "DATA_EXFILTRATION",
    "MALWARE_DOWNLOAD",
    "LATERAL_MOVEMENT",
    "DNS_TUNNELING",
    "CRYPTO_MINING"
]


@dataclass
class ModelConfig:
    model_type: str = "isolation_forest"
    contamination: float = 0.01
    n_estimators: int = 100
    max_samples: str = "auto"
    random_state: int = 42
    n_jobs: int = -1
    threshold_percentile: float = 99.0
    feature_columns: List[str] = None
    
    def __post_init__(self):
        if self.feature_columns is None:
            self.feature_columns = FEATURE_COLUMNS


class BaseDetector:
    @abstractmethod
    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'BaseDetector':
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        pass
    
    @abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray:
        pass
    
    @abstractmethod
    def save(self, path: str):
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, path: str) -> 'BaseDetector':
        pass


class IsolationForestDetector(BaseDetector):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.scaler = RobustScaler()
        self.model = IsolationForest(
            n_estimators=config.n_estimators,
            max_samples=config.max_samples,
            contamination=config.contamination,
            random_state=config.random_state,
            n_jobs=config.n_jobs,
            verbose=0
        )
        self.threshold = None
        self.is_fitted = False

    def _extract_features(self, flow_dict: Dict) -> np.ndarray:
        features = []
        for col in self.config.feature_columns:
            val = flow_dict.get(col, 0)
            if isinstance(val, dict):
                val = sum(val.values())
            features.append(float(val))
        return np.array(features).reshape(1, -1)

    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'IsolationForestDetector':
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        scores = -self.model.score_samples(X_scaled)
        self.threshold = np.percentile(scores, self.config.threshold_percentile)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        scores = -self.model.score_samples(X_scaled)
        return (scores > self.threshold).astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        return -self.model.score_samples(X_scaled)

    def predict_single(self, flow_dict: Dict) -> Tuple[int, float]:
        X = self._extract_features(flow_dict)
        anomaly_score = self.score(X)[0]
        is_anomaly = int(anomaly_score > self.threshold)
        return is_anomaly, float(anomaly_score)

    def save(self, path: str):
        model_data = {
            "config": self.config.__dict__,
            "scaler": self.scaler,
            "model": self.model,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted
        }
        joblib.dump(model_data, path)

    @classmethod
    def load(cls, path: str) -> 'IsolationForestDetector':
        model_data = joblib.load(path)
        detector = cls(ModelConfig(**model_data["config"]))
        detector.scaler = model_data["scaler"]
        detector.model = model_data["model"]
        detector.threshold = model_data["threshold"]
        detector.is_fitted = model_data["is_fitted"]
        return detector

    def export_onnx(self, path: str, input_shape: Tuple[int, int] = (1, len(FEATURE_COLUMNS))):
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX tools not available")
        
        initial_type = [('float_input', FloatTensorType(input_shape))]
        onnx_model = convert_sklearn(
            self.model,
            initial_types=initial_type,
            target_opset=12
        )
        with open(path, "wb") as f:
            f.write(onnx_model.SerializeToString())


class AutoencoderDetector(BaseDetector):
    def __init__(self, config: ModelConfig, input_dim: int = len(FEATURE_COLUMNS)):
        self.config = config
        self.input_dim = input_dim
        self.scaler = StandardScaler()
        self.model = None
        self.threshold = None
        self.is_fitted = False
        self._build_model()

    def _build_model(self):
        try:
            import tensorflow as tf
            from tensorflow.keras import layers, models, optimizers
            
            encoding_dim = max(8, self.input_dim // 4)
            
            input_layer = layers.Input(shape=(self.input_dim,))
            encoded = layers.Dense(64, activation='relu')(input_layer)
            encoded = layers.Dense(32, activation='relu')(encoded)
            encoded = layers.Dense(encoding_dim, activation='relu')(encoded)
            decoded = layers.Dense(32, activation='relu')(encoded)
            decoded = layers.Dense(64, activation='relu')(decoded)
            decoded = layers.Dense(self.input_dim, activation='linear')(decoded)
            
            self.model = models.Model(input_layer, decoded)
            self.model.compile(optimizer='adam', loss='mse')
            self.tf = tf
        except ImportError:
            print("TensorFlow not available, using sklearn MLP fallback")
            from sklearn.neural_network import MLPRegressor
            self.model = MLPRegressor(
                hidden_layer_sizes=(64, 32, 16, 32, 64),
                activation='relu',
                solver='adam',
                max_iter=500,
                random_state=self.config.random_state
            )
            self.tf = None

    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'AutoencoderDetector':
        X_scaled = self.scaler.fit_transform(X)
        
        if self.tf:
            self.model.fit(X_scaled, X_scaled, epochs=50, batch_size=256, verbose=0, validation_split=0.1)
            reconstructions = self.model.predict(X_scaled, verbose=0)
        else:
            self.model.fit(X_scaled, X_scaled)
            reconstructions = self.model.predict(X_scaled)
        
        mse = np.mean(np.square(X_scaled - reconstructions), axis=1)
        self.threshold = np.percentile(mse, self.config.threshold_percentile)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        scores = self.score(X)
        return (scores > self.threshold).astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        
        if self.tf:
            reconstructions = self.model.predict(X_scaled, verbose=0)
        else:
            reconstructions = self.model.predict(X_scaled)
        
        mse = np.mean(np.square(X_scaled - reconstructions), axis=1)
        return mse

    def save(self, path: str):
        model_data = {
            "config": self.config.__dict__,
            "scaler": self.scaler,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted,
            "input_dim": self.input_dim
        }
        joblib.dump(model_data, path.replace('.pkl', '_meta.pkl'))
        if self.tf:
            self.model.save(path.replace('.pkl', '_tf'))
        else:
            joblib.dump(self.model, path.replace('.pkl', '_sklearn.pkl'))

    @classmethod
    def load(cls, path: str) -> 'AutoencoderDetector':
        model_data = joblib.load(path.replace('.pkl', '_meta.pkl'))
        detector = cls(ModelConfig(**model_data["config"]), model_data["input_dim"])
        detector.scaler = model_data["scaler"]
        detector.threshold = model_data["threshold"]
        detector.is_fitted = model_data["is_fitted"]
        if detector.tf:
            detector.model = detector.tf.keras.models.load_model(path.replace('.pkl', '_tf'))
        else:
            detector.model = joblib.load(path.replace('.pkl', '_sklearn.pkl'))
        return detector


class SupervisedDetector(BaseDetector):
    def __init__(self, config: ModelConfig, n_classes: int = len(ATTACK_LABELS)):
        self.config = config
        self.n_classes = n_classes
        self.scaler = StandardScaler()
        self.label_encoder = {i: label for i, label in enumerate(ATTACK_LABELS)}
        
        if LIGHTGBM_AVAILABLE:
            self.model = lgb.LGBMClassifier(
                n_estimators=config.n_estimators,
                random_state=config.random_state,
                n_jobs=config.n_jobs,
                verbosity=-1,
                class_weight='balanced'
            )
            self.use_lgbm = True
        else:
            from sklearn.ensemble import RandomForestClassifier
            self.model = RandomForestClassifier(
                n_estimators=config.n_estimators,
                random_state=config.random_state,
                n_jobs=config.n_jobs,
                class_weight='balanced'
            )
            self.use_lgbm = False
        
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'SupervisedDetector':
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        return self.model.predict_proba(X_scaled)

    def score(self, X: np.ndarray) -> np.ndarray:
        proba = self.predict_proba(X)
        return 1 - np.max(proba, axis=1)

    def save(self, path: str):
        model_data = {
            "config": self.config.__dict__,
            "scaler": self.scaler,
            "model": self.model,
            "label_encoder": self.label_encoder,
            "is_fitted": self.is_fitted,
            "use_lgbm": self.use_lgbm
        }
        joblib.dump(model_data, path)

    @classmethod
    def load(cls, path: str) -> 'SupervisedDetector':
        model_data = joblib.load(path)
        detector = cls(ModelConfig(**model_data["config"]))
        detector.scaler = model_data["scaler"]
        detector.model = model_data["model"]
        detector.label_encoder = model_data["label_encoder"]
        detector.is_fitted = model_data["is_fitted"]
        detector.use_lgbm = model_data["use_lgbm"]
        return detector


class EnsembleDetector:
    def __init__(self, detectors: List[BaseDetector], weights: Optional[List[float]] = None):
        self.detectors = detectors
        self.weights = weights or [1.0] * len(detectors)
        self.threshold = 0.5

    def predict(self, X: np.ndarray) -> np.ndarray:
        scores = self.score(X)
        return (scores > self.threshold).astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        weighted_scores = np.zeros(len(X))
        for detector, weight in zip(self.detectors, self.weights):
            weighted_scores += weight * detector.score(X)
        return weighted_scores / sum(self.weights)

    def predict_single(self, flow_dict: Dict, feature_extractor) -> Tuple[int, float, Dict[str, float]]:
        X = feature_extractor(flow_dict).reshape(1, -1)
        individual_scores = {}
        for i, detector in enumerate(self.detectors):
            individual_scores[type(detector).__name__] = float(detector.score(X)[0])
        
        ensemble_score = self.score(X)[0]
        is_anomaly = int(ensemble_score > self.threshold)
        return is_anomaly, float(ensemble_score), individual_scores

    def calibrate_threshold(self, X: np.ndarray, target_fpr: float = 0.01):
        scores = self.score(X)
        self.threshold = np.percentile(scores, (1 - target_fpr) * 100)


class ModelTrainer:
    def __init__(self, data_path: str, model_dir: str = "models"):
        self.data_path = data_path
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

    def load_data(self) -> Tuple[np.ndarray, np.ndarray]:
        if self.data_path.endswith('.csv'):
            df = pd.read_csv(self.data_path)
        elif self.data_path.endswith('.parquet'):
            df = pd.read_parquet(self.data_path)
        else:
            raise ValueError("Unsupported data format")
        
        X = df[FEATURE_COLUMNS].values
        y = df['label'].values if 'label' in df.columns else None
        return X, y

    def train_isolation_forest(self, X: np.ndarray, config: ModelConfig) -> IsolationForestDetector:
        detector = IsolationForestDetector(config)
        detector.fit(X)
        detector.save(str(self.model_dir / "isolation_forest.pkl"))
        if ONNX_AVAILABLE:
            detector.export_onnx(str(self.model_dir / "isolation_forest.onnx"))
        return detector

    def train_autoencoder(self, X: np.ndarray, config: ModelConfig) -> AutoencoderDetector:
        detector = AutoencoderDetector(config, X.shape[1])
        detector.fit(X)
        detector.save(str(self.model_dir / "autoencoder.pkl"))
        return detector

    def train_supervised(self, X: np.ndarray, y: np.ndarray, config: ModelConfig) -> SupervisedDetector:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        detector = SupervisedDetector(config)
        detector.fit(X_train, y_train)
        
        y_pred = detector.predict(X_test)
        print(classification_report(y_test, y_pred, target_names=ATTACK_LABELS))
        
        detector.save(str(self.model_dir / "supervised.pkl"))
        return detector

    def train_ensemble(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> EnsembleDetector:
        config = ModelConfig()
        
        iso = self.train_isolation_forest(X, config)
        ae = self.train_autoencoder(X, config)
        
        detectors = [iso, ae]
        weights = [0.6, 0.4]
        
        if y is not None:
            sup = self.train_supervised(X, y, config)
            detectors.append(sup)
            weights.append(0.5)
        
        ensemble = EnsembleDetector(detectors, weights)
        
        if y is not None:
            ensemble.calibrate_threshold(X, target_fpr=0.01)
        else:
            ensemble.calibrate_threshold(X, target_fpr=0.01)
        
        return ensemble


def generate_synthetic_data(n_samples: int = 10000, contamination: float = 0.02) -> Tuple[np.ndarray, np.ndarray]:
    np.random.seed(42)
    n_normal = int(n_samples * (1 - contamination))
    n_anomaly = n_samples - n_normal
    
    normal_data = np.random.randn(n_normal, len(FEATURE_COLUMNS))
    normal_data[:, 0] = np.abs(normal_data[:, 0]) * 1000 + 100
    normal_data[:, 1:3] = np.abs(normal_data[:, 1:3]) * 10 + 1
    normal_data[:, 3:5] = np.abs(normal_data[:, 3:5]) * 1000 + 500
    normal_data[:, 5:9] = np.abs(normal_data[:, 5:9]) * 10 + 5
    normal_data[:, 9:13] = np.abs(normal_data[:, 9:13]) * 200 + 500
    normal_data[:, 13:23] = np.random.poisson(5, (n_normal, 10))
    normal_data[:, 23:25] = np.random.uniform(3, 7, (n_normal, 2))
    normal_data[:, 25] = np.random.choice([1, 6, 17], n_normal, p=[0.05, 0.7, 0.25])
    normal_data[:, 26:28] = np.random.randint(1, 3, (n_normal, 2))
    
    anomaly_data = np.random.randn(n_anomaly, len(FEATURE_COLUMNS)) * 5
    anomaly_data[:, 0] = np.abs(anomaly_data[:, 0]) * 5000 + 10000
    anomaly_data[:, 1:3] = np.abs(anomaly_data[:, 1:3]) * 1000 + 100
    anomaly_data[:, 3:5] = np.abs(anomaly_data[:, 3:5]) * 10000 + 10000
    anomaly_data[:, 5:9] = np.abs(anomaly_data[:, 5:9]) * 100 + 100
    anomaly_data[:, 9:13] = np.abs(anomaly_data[:, 9:13]) * 1000 + 1000
    anomaly_data[:, 13:23] = np.random.poisson(50, (n_anomaly, 10))
    anomaly_data[:, 23:25] = np.random.uniform(7.5, 8.0, (n_anomaly, 2))
    anomaly_data[:, 25] = np.random.choice([6, 17], n_anomaly)
    anomaly_data[:, 26:28] = np.random.randint(3, 5, (n_anomaly, 2))
    
    X = np.vstack([normal_data, anomaly_data])
    y = np.hstack([np.zeros(n_normal), np.ones(n_anomaly)])
    
    indices = np.random.permutation(n_samples)
    return X[indices], y[indices]


class AnomalyDetector:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.scaler = RobustScaler()
        self.model = IsolationForest(
            n_estimators=config.n_estimators,
            max_samples=config.max_samples,
            contamination=config.contamination,
            random_state=config.random_state,
            n_jobs=config.n_jobs,
            verbose=0
        )
        self.threshold = None
        self.is_fitted = False

    def _extract_features(self, flow_dict: Dict) -> np.ndarray:
        features = []
        for col in self.config.feature_columns:
            val = flow_dict.get(col, 0)
            if isinstance(val, dict):
                tcp_map = {"SYN": 0, "ACK": 1, "FIN": 2, "RST": 3, "PSH": 4}
                if "tcp_" in col and "_fwd" in col:
                    flag = col.replace("tcp_", "").replace("_fwd", "").upper()
                    val = flow_dict.get("tcp_flags_fwd", {}).get(flag, 0)
                elif "tcp_" in col and "_bwd" in col:
                    flag = col.replace("tcp_", "").replace("_bwd", "").upper()
                    val = flow_dict.get("tcp_flags_bwd", {}).get(flag, 0)
                else:
                    val = sum(val.values()) if isinstance(val, dict) else 0
            features.append(float(val))
        return np.array(features).reshape(1, -1)

    def fit(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> 'AnomalyDetector':
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        scores = -self.model.score_samples(X_scaled)
        self.threshold = np.percentile(scores, self.config.threshold_percentile)
        self.is_fitted = True
        return self
    
    def train(self, X: np.ndarray) -> dict:
        """Train the model and return training info (compatible with test interface)."""
        self.fit(X)
        return {
            'samples': X.shape[0],
            'threshold': self.threshold,
            'is_fitted': self.is_fitted
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        scores = -self.model.score_samples(X_scaled)
        return (scores > self.threshold).astype(int)

    def score(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        X_scaled = self.scaler.transform(X)
        return -self.model.score_samples(X_scaled)

    def _classify_threat(self, flow_dict: Dict) -> str:
        """Classify the type of threat based on flow features."""
        # DDoS indicators
        if flow_dict.get("packet_rate", 0) > 5000:
            return "DDoS"
        
        # SYN Flood
        if flow_dict.get("syn_ratio", 0) > 0.8 and flow_dict.get("packet_rate", 0) > 100:
            return "SYN_FLOOD"
        
        # Port Scan
        if flow_dict.get("avg_packet_size", 1500) < 100 and flow_dict.get("packet_rate", 0) > 50:
            return "PORT_SCAN"
        
        # UDP Flood
        if flow_dict.get("protocol_udp", 0) > flow_dict.get("protocol_tcp", 0) * 2:
            if flow_dict.get("packet_rate", 0) > 100:
                return "UDP_FLOOD"
        
        # Brute Force
        if flow_dict.get("packet_count", 0) > 10 and flow_dict.get("avg_packet_size", 0) < 200:
            if flow_dict.get("dst_port") in [22, 21, 23, 3389, 445]:
                return "BRUTE_FORCE"
        
        # Data Exfiltration
        if flow_dict.get("fwd_byte_ratio", 0) > 0.9 and flow_dict.get("byte_count", 0) > 10_000_000:
            return "DATA_EXFILTRATION"
        
        # C2 Beaconing
        if flow_dict.get("std_iat", 0) < 0.1 and flow_dict.get("avg_iat", 0) > 1:
            return "C2_BEACONING"
        
        return "UNKNOWN"

    def predict_single(self, flow_dict: Dict) -> Tuple[int, float, dict]:
        X = self._extract_features(flow_dict)
        anomaly_score = self.score(X)[0]
        is_anomaly = int(anomaly_score > self.threshold)
        normalized_score = max(0.0, min(1.0, (self.threshold - anomaly_score) / abs(self.threshold + 0.1)))
        threat_type = self._classify_threat(flow_dict)
        details = {
            "score": float(anomaly_score),
            "normalized_score": float(normalized_score),
            "threshold": float(self.threshold),
            "threat_type": threat_type,
            "features_used": list(flow_dict.keys())
        }
        return is_anomaly, float(normalized_score), details

    def save(self, path: str):
        model_data = {
            "config": self.config.__dict__,
            "scaler": self.scaler,
            "model": self.model,
            "threshold": self.threshold,
            "is_fitted": self.is_fitted
        }
        joblib.dump(model_data, path)

    @classmethod
    def load(cls, path: str) -> 'AnomalyDetector':
        model_data = joblib.load(path)
        detector = cls(ModelConfig(**model_data["config"]))
        detector.scaler = model_data["scaler"]
        detector.model = model_data["model"]
        detector.threshold = model_data["threshold"]
        detector.is_fitted = model_data["is_fitted"]
        return detector

    def export_onnx(self, path: str, input_shape: Tuple[int, int] = (1, len(FEATURE_COLUMNS))):
        if not ONNX_AVAILABLE:
            raise RuntimeError("ONNX tools not available")
        
        initial_type = [('float_input', FloatTensorType(input_shape))]
        onnx_model = convert_sklearn(
            self.model,
            initial_types=initial_type,
            target_opset=12
        )
        with open(path, "wb") as f:
            f.write(onnx_model.SerializeToString())
    
    def get_stats(self) -> dict:
        """Get statistics about the model."""
        return {
            "is_fitted": self.is_fitted,
            "threshold": self.threshold,
            "n_estimators": self.model.n_estimators if hasattr(self.model, 'n_estimators') else 0,
            "contamination": self.config.contamination,
            "feature_count": len(FEATURE_COLUMNS),
            "anomaly_count": 0,  # This would be tracked separately
            "model_type": "IsolationForest"
        }


class AnomalyDetectionService:
    """Service that combines feature extraction with anomaly detection."""
    
    def __init__(self):
        self.detector = AnomalyDetector(ModelConfig())
        self.processor = None
        self._retrain_task: Optional[asyncio.Task] = None
        self._retrain_buffer: list[dict] = []
        self._buffer_lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        model_path = Path("ml/models/anomaly_detector.pkl")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        if model_path.exists():
            self.detector = self.detector.load(model_path)
            logger.info("Loaded pre-trained model")
        else:
            logger.info("No pre-trained model found. Training with synthetic data...")
            from backend.ml.model import generate_synthetic_data
            X, y = generate_synthetic_data(5000, 0.05)
            self.detector.fit(X)
            self.detector.save(model_path)
            logger.info("Model trained and saved")
        
        self._retrain_task = asyncio.create_task(self._retrain_loop())
    
    async def process_features(self, features: dict) -> dict:
        is_anomaly, score, details = self.detector.predict_single(features)
        
        features["anomaly"] = bool(details.get("anomaly", False))
        features["threat_score"] = details.get("normalized_score", 0.0)
        features["threat_type"] = details.get("threat_type", "UNKNOWN")
        features["threat_details"] = details
        
        async with self._buffer_lock:
            self._retrain_buffer.append(features)
            if len(self._retrain_buffer) > 10000:
                self._retrain_buffer = self._retrain_buffer[-5000:]
        
        return features
    
    async def _retrain_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # 24 hours
                
                async with self._buffer_lock:
                    if len(self._retrain_buffer) >= 1000:
                        logger.info(f"Retraining model with {len(self._retrain_buffer)} new samples...")
                        try:
                            normal_samples = [
                                f for f in self._retrain_buffer
                                if not f.get("anomaly", False)
                            ]
                            
                            if len(normal_samples) >= 500:
                                result = self.detector.train(normal_samples)
                                logger.info(f"Retraining complete: {result}")
                            else:
                                logger.warning("Not enough normal samples for retraining")
                            
                            self._retrain_buffer.clear()
                        except Exception as e:
                            logger.error(f"Retrain inner loop error: {e}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retrain loop error: {e}")
    
    async def shutdown(self) -> None:
        if self._retrain_task:
            self._retrain_task.cancel()
            try:
                await self._retrain_task
            except asyncio.CancelledError:
                pass


anomaly_detector = AnomalyDetector(ModelConfig())
detection_service = AnomalyDetectionService()