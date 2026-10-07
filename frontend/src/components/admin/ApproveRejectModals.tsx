import React, { useState } from 'react';
import { ShieldAlert } from 'lucide-react';
import { Button } from '../ui/Button';
import { MLModelItem } from '../../api/models';

interface ApproveModalProps {
  target: MLModelItem | null;
  onClose: () => void;
  onConfirm: (force: boolean) => Promise<void>;
}

export const ApproveModal: React.FC<ApproveModalProps> = ({ target, onClose, onConfirm }) => {
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!target) return null;

  const r2 = target.metrics_json?.random_split?.r2 ?? 1;
  const rmse = target.metrics_json?.random_split?.rmse ?? 0;
  const failsThreshold = r2 < 0.70 || rmse > 1.50;

  const handleConfirm = async () => {
    setLoading(true);
    await onConfirm(force);
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-xl text-xs space-y-4">
        <h3 className="text-base font-bold text-foreground">Approve Model: {target.version}</h3>
        <p className="text-muted-foreground">
          Promoting this candidate will hot swap the active microservice model with zero downtime and archive the current production model.
        </p>

        {failsThreshold && (
          <div className="rounded-md bg-destructive/15 p-3 text-destructive space-y-2">
            <span className="font-bold flex items-center">
              <ShieldAlert className="mr-1 h-4 w-4" /> Quality Gate Warning
            </span>
            <p>
              Model fails minimum quality thresholds (R² &ge; 0.70, RMSE &le; 1.50). Approval will be rejected unless forced.
            </p>
            <label className="flex items-center space-x-2 cursor-pointer font-bold mt-2">
              <input
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                className="rounded text-destructive"
              />
              <span>Force approval with administrative override audit</span>
            </label>
          </div>
        )}

        <div className="flex justify-end space-x-2 pt-2">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={loading || (failsThreshold && !force)}>
            Confirm Hot Swap
          </Button>
        </div>
      </div>
    </div>
  );
};

interface RejectModalProps {
  target: MLModelItem | null;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
}

export const RejectModal: React.FC<RejectModalProps> = ({ target, onClose, onConfirm }) => {
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);

  if (!target) return null;

  const handleConfirm = async () => {
    if (!reason.trim()) return;
    setLoading(true);
    await onConfirm(reason.trim());
    setLoading(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-xl border bg-card p-6 shadow-xl text-xs space-y-4">
        <h3 className="text-base font-bold text-foreground">Reject Candidate: {target.version}</h3>
        <p className="text-muted-foreground">
          Provide mandatory architectural or performance reasoning for audit compliance.
        </p>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Unstable residual distribution on extreme temperature anomalies..."
          className="w-full rounded-md border bg-background p-2 text-xs h-24"
        />
        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={loading || !reason.trim()}
            onClick={handleConfirm}
          >
            Reject Model
          </Button>
        </div>
      </div>
    </div>
  );
};
