
/* ================================
   SURE WINS COMPACT MATCH LIST
================================ */

.match-row {
    display: grid;
    grid-template-columns: 48px 1fr auto 25px;
    align-items: center;
    gap: 14px;
    padding: 16px;
    margin-bottom: 10px;

    background: #121c2b;
    border: 1px solid #243247;
    border-radius: 14px;

    cursor: pointer;
    transition: transform .2s ease, border-color .2s ease;
}

.match-row:hover {
    transform: translateY(-2px);
    border-color: #35d07f;
}

.match-rank {
    font-size: 14px;
    font-weight: bold;
    color: #718096;
}

.match-main {
    min-width: 0;
}

.match-teams {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    font-size: 16px;
}

.match-teams span {
    color: #6f7d91;
    font-size: 12px;
}

.match-meta {
    display: flex;
    gap: 10px;
    margin-top: 7px;
    font-size: 11px;
    color: #8490a3;
}

.row-tier {
    color: #49df91;
    font-weight: bold;
    text-transform: uppercase;
}

.match-confidence {
    text-align: right;
}

.match-confidence strong {
    display: block;
    color: #55e69b;
    font-size: 18px;
}

.match-confidence small {
    color: #718096;
    font-size: 10px;
}

.match-arrow {
    color: #55e69b;
    font-size: 28px;
}


/* ================================
   ANALYSIS MODAL
================================ */

.analysis-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.detail-tier {
    padding: 7px 12px;
    border-radius: 20px;
    background: rgba(53, 208, 127, .12);
    color: #55e69b;
    font-weight: bold;
}

.modal-close-inline {
    border: none;
    background: #202b3c;
    color: white;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    font-size: 24px;
    cursor: pointer;
}

.analysis-teams {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: center;
    gap: 15px;
    text-align: center;
    margin: 28px 0;
}

.analysis-teams small {
    color: #718096;
    font-size: 10px;
    letter-spacing: 1px;
}

.analysis-teams h2 {
    margin: 8px 0;
    font-size: 21px;
}

.analysis-vs {
    color: #718096;
    font-weight: bold;
}


.confidence-section {
    padding: 18px;
    border-radius: 14px;
    background: #182334;
}

.confidence-top {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
}

.confidence-top span {
    color: #a6b0bf;
}

.confidence-top strong {
    color: #55e69b;
}

.confidence-track {
    height: 9px;
    overflow: hidden;
    border-radius: 20px;
    background: #26364c;
}

.confidence-progress {
    height: 100%;
    border-radius: 20px;
    background: linear-gradient(90deg, #25c778, #66e5a5);
}


.analysis-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin: 20px 0;
}

.analysis-stats div {
    padding: 14px;
    background: #182334;
    border-radius: 12px;
}

.analysis-stats small {
    display: block;
    margin-bottom: 6px;
    color: #718096;
    font-size: 10px;
}

.analysis-stats strong {
    color: white;
}


.analysis-section {
    padding: 18px;
    border-radius: 14px;
    background: #182334;
}

.analysis-section h3 {
    margin-top: 0;
}

.analysis-section p {
    color: #b4bdca;
    line-height: 1.6;
}


.coming-next {
    margin-top: 14px;
    padding: 16px;
    border: 1px solid #26364c;
    border-radius: 12px;
}

.coming-next div {
    font-weight: bold;
    margin-bottom: 6px;
}

.coming-next small {
    color: #718096;
}


/* MOBILE */

@media (max-width: 600px) {

    .match-row {
        grid-template-columns: 34px 1fr auto;
        gap: 10px;
    }

    .match-arrow {
        display: none;
    }

    .match-teams {
        font-size: 14px;
    }

    .match-confidence strong {
        font-size: 16px;
    }

    .analysis-teams h2 {
        font-size: 16px;
    }

    .analysis-stats {
        grid-template-columns: 1fr;
    }
}
