import React, { useState, useEffect } from 'react'
import api from './api'
import toast from 'react-hot-toast'
import { QrCode, RefreshCcw, Download } from 'lucide-react'

export default function MerchantQR() {
    const [qrUrl, setQrUrl] = useState(null)
    const [loading, setLoading] = useState(true)

    const fetchQR = async () => {
        setLoading(true)
        try {
            // We use standard fetch or api config to get blob
            const res = await api.get('/merchants/me/qr-code', { responseType: 'blob' })
            const url = URL.createObjectURL(res.data)
            setQrUrl(url)
        } catch (err) {
            toast.error('Failed to load QR code')
        } finally {
            setLoading(false)
        }
    }

    const regenerateQR = async () => {
        if (!window.confirm("Regenerating will invalidate your old QR code. Continue?")) return;
        setLoading(true)
        try {
            await api.post('/merchants/me/qr-code/regenerate')
            toast.success("QR Code Regenerated!")
            fetchQR()
        } catch (err) {
            toast.error('Failed to regenerate QR code')
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchQR()
        return () => {
            if (qrUrl) URL.revokeObjectURL(qrUrl)
        }
    }, [])

    return (
        <div className="panel glass">
            <div className="panel-header">
                <div>
                    <h2 className="panel-title">My Shop QR Code</h2>
                    <p className="panel-sub">Customers can scan this to pay you directly</p>
                </div>
                <QrCode size={22} className="text-accent" />
            </div>

            <div className="flex-col" style={{ alignItems: 'center', marginTop: '20px' }}>
                {loading ? (
                    <div className="spinner" style={{ width: 40, height: 40, margin: '50px 0' }} />
                ) : qrUrl ? (
                    <div style={{ background: 'white', padding: '16px', borderRadius: '16px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
                        <img src={qrUrl} alt="Merchant QR Code" style={{ width: 250, height: 250 }} />
                    </div>
                ) : (
                    <p>No QR Code available</p>
                )}

                <div style={{ display: 'flex', gap: '12px', marginTop: '30px' }}>
                    <button className="btn-primary" onClick={regenerateQR} disabled={loading} style={{ background: 'rgba(255,100,100,0.2)', color: '#ff8888', border: '1px solid rgba(255,100,100,0.4)' }}>
                        <RefreshCcw size={18} /> Regenerate QR
                    </button>
                    {qrUrl && (
                        <a href={qrUrl} download="merchant-qr.png" className="btn-primary" style={{ textDecoration: 'none' }}>
                            <Download size={18} /> Download
                        </a>
                    )}
                </div>
            </div>
        </div>
    )
}
