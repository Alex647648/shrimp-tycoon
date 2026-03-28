import { useState, useEffect } from 'react';
import { ROIData } from '../types/api';

export function useShrimpData() {
  const [roi, setRoi] = useState<ROIData>({
    revenue: 34600,
    multiplier: 2.5,
    survival_count: 412,
    avg_weight: 35,
    total_biomass: 14.4,
    market_price: 26.7,
    saas_fee: 2000,
    risk_mitigation: 8000
  });

  const fetchROI = async () => {
    try {
      const response = await fetch('/api/roi');
      if (response.ok) {
        const data = await response.json();
        setRoi(data);
      }
    } catch (e) {
      console.error('Failed to fetch ROI data:', e);
    }
  };

  useEffect(() => {
    fetchROI();
    const interval = setInterval(fetchROI, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  return { roi };
}
