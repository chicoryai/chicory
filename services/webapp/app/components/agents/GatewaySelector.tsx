import { useState, useEffect } from 'react';
import { getMcpGateways, type MCPGateway } from '~/services/chicory.server';

interface GatewaySelectorProps {
  projectId: string;
  selectedGatewayId?: string;
  onSelectGateway: (gatewayId: string) => void;
  disabled?: boolean;
  gateways?: MCPGateway[];
}

export default function GatewaySelector({
  projectId,
  selectedGatewayId,
  onSelectGateway,
  disabled = false,
  gateways = []
}: GatewaySelectorProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSelectGateway(e.target.value);
  };

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 dark:bg-gray-700 rounded"></div>
      </div>
    );
  }

  if (gateways.length === 0) {
    return (
      <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <p className="text-sm text-yellow-800 dark:text-yellow-200">
          No gateways available. Please create a gateway first.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <label htmlFor="gateway-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        Select Gateway
      </label>
      <select
        id="gateway-select"
        value={selectedGatewayId || ''}
        onChange={handleSelectChange}
        disabled={disabled}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
        required
      >
        <option value="">Choose a gateway...</option>
        {gateways.map((gateway) => (
          <option key={gateway.id} value={gateway.id}>
            {gateway.name}
          </option>
        ))}
      </select>
      {selectedGatewayId && (
        <div className="mt-2">
          {gateways.find(g => g.id === selectedGatewayId) && (
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {gateways.find(g => g.id === selectedGatewayId)?.description || 'No description available'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}