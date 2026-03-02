import React, { useState, useEffect } from 'react';
import { healthCheck } from '../services/api';

const BackendDebugger = () => {
    const [status, setStatus] = useState('checking');
    const [details, setDetails] = useState(null);
    const [apiUrl, setApiUrl] = useState('');

    useEffect(() => {
        // Get API URL from environment
        const url = process.env.REACT_APP_API_URL || '(not set)';
        setApiUrl(url);

        // Run health check
        const checkHealth = async () => {
            try {
                const isHealthy = await healthCheck();
                setStatus(isHealthy ? 'healthy' : 'unhealthy');
                
                // Try to get more details
                try {
                    const response = await fetch(`${url}/health`);
                    const data = await response.json();
                    setDetails({
                        status: response.status,
                        data: data,
                        headers: Object.fromEntries(response.headers.entries())
                    });
                } catch (err) {
                    setDetails({
                        error: err.message,
                        code: err.code
                    });
                }
            } catch (error) {
                setStatus('error');
                setDetails({
                    error: error.message,
                    code: error.code
                });
            }
        };

        checkHealth();
    }, []);

    const testEndpoint = async (endpoint) => {
        try {
            const url = process.env.REACT_APP_API_URL;
            const response = await fetch(`${url}${endpoint}`);
            const text = await response.text();
            return {
                status: response.status,
                ok: response.ok,
                data: text
            };
        } catch (error) {
            return {
                error: error.message,
                code: error.code
            };
        }
    };

    const getStatusColor = () => {
        switch (status) {
            case 'healthy': return '#0c0';
            case 'unhealthy': return '#f90';
            case 'error': return '#c00';
            default: return '#666';
        }
    };

    const getStatusText = () => {
        switch (status) {
            case 'healthy': return '✅ Connected';
            case 'unhealthy': return '⚠️ Connection Issue';
            case 'error': return '❌ Cannot Connect';
            default: return '🔄 Checking...';
        }
    };

    return (
        <div style={{
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            background: '#fff',
            border: `2px solid ${getStatusColor()}`,
            borderRadius: '8px',
            padding: '16px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            maxWidth: '400px',
            zIndex: 9999,
            fontSize: '14px'
        }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', color: getStatusColor() }}>
                {getStatusText()}
            </div>
            
            <div style={{ marginBottom: '8px' }}>
                <strong>API URL:</strong> {apiUrl || '(not set)'}
            </div>

            {details && (
                <div style={{ marginTop: '12px', fontSize: '12px' }}>
                    {details.error ? (
                        <div style={{ color: '#c00' }}>
                            <strong>Error:</strong> {details.error}
                            {details.code && <div>Code: {details.code}</div>}
                        </div>
                    ) : (
                        <div>
                            <div><strong>Status:</strong> {details.status}</div>
                            {details.data && (
                                <div style={{ marginTop: '4px', fontFamily: 'monospace', fontSize: '11px' }}>
                                    {JSON.stringify(details.data, null, 2)}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            <div style={{ marginTop: '12px', fontSize: '11px', color: '#666' }}>
                Check browser console for detailed logs
            </div>
        </div>
    );
};

export default BackendDebugger;
