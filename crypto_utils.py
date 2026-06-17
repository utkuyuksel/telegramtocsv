import requests

import config

# keccak256("Transfer(address,address,uint256)") — the ERC-20/BEP-20 Transfer topic
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TRONSCAN_TX_URL = "https://apilist.tronscanapi.com/api/transaction-info"


def verify_payment(network, txid, expected_amount):
    """
    Verify a USDT payment to our wallet on the given network (TRC20/ERC20/BEP20).

    Returns (True, "Success") on success, (False, reason) on failure.
    Fails CLOSED: any error/timeout returns (False, reason), never (True, ...).
    All amount math is done in raw integer units using the network's own
    decimals (6 on TRON/Ethereum, 18 on BSC) to avoid float drift / decimal bugs.
    """
    net = config.USDT_NETWORKS.get((network or "").upper())
    if not net:
        return False, "Unsupported payment network."
    if not net.get("wallet"):
        return False, "Server wallet not configured for this network."
    if not txid or len(txid) < 20:
        return False, "Invalid TXID."

    try:
        if net["kind"] == "tron":
            return _verify_trc20(net, txid, expected_amount)
        return _verify_evm(net, txid, expected_amount)
    except requests.RequestException as e:
        return False, f"Network error contacting node: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"


def verify_txid(txid, expected_amount, currency="USDT"):
    """Back-compat alias (TRC20) for any caller still importing verify_txid."""
    return verify_payment("TRC20", txid, expected_amount)


def _raw(amount, decimals):
    """Convert a human USDT amount to raw integer token units."""
    return round(amount * (10 ** decimals))


def _rpc(urls, method, params):
    """
    Call a JSON-RPC method, trying each URL in order until one responds.
    Returns the 'result' (which may be None, e.g. tx not found / pending).
    Raises requests.RequestException if EVERY endpoint fails (-> fail closed).
    """
    if isinstance(urls, str):
        urls = [urls]
    last = None
    for url in urls:
        if not url:
            continue
        try:
            r = requests.post(
                url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=15,
            )
            j = r.json()
            if "result" in j:
                return j["result"]
            last = j.get("error")
        except Exception as e:
            last = e
            continue
    raise requests.RequestException(f"All RPC endpoints failed: {last}")


def _verify_evm(net, txid, expected_amount):
    """Verify a USDT transfer on an EVM chain (Ethereum / BSC) via JSON-RPC."""
    if not (txid.startswith("0x") and len(txid) == 66):
        return False, "Invalid EVM transaction hash."

    urls = net["rpc"]
    receipt = _rpc(urls, "eth_getTransactionReceipt", [txid])
    if not receipt:
        return False, "Transaction not found or not yet confirmed."
    if receipt.get("status") != "0x1":
        return False, "Transaction failed on chain."

    # Optional confirmation depth (cheap re-org guard).
    min_conf = net.get("min_confirmations", 1)
    if min_conf > 1:
        latest = int(_rpc(urls, "eth_blockNumber", []), 16)
        blk = int(receipt["blockNumber"], 16)
        if latest - blk + 1 < min_conf:
            return False, "Not enough confirmations yet. Please try again shortly."

    contract = net["contract"].lower()
    wallet = net["wallet"].lower()
    decimals = net["decimals"]

    total_raw = 0
    for log in receipt.get("logs", []):
        if (log.get("address") or "").lower() != contract:  # right token only
            continue
        topics = log.get("topics") or []
        if len(topics) != 3 or topics[0].lower() != TRANSFER_TOPIC:  # is a Transfer
            continue
        to_addr = "0x" + topics[2][-40:]  # last 20 bytes of the indexed 'to'
        if to_addr.lower() != wallet:  # right recipient
            continue
        total_raw += int(log.get("data") or "0x0", 16)  # uint256 amount

    if total_raw == 0:
        return False, "No USDT transfer to our wallet found in this transaction."

    if total_raw + _raw(0.001, decimals) < _raw(expected_amount, decimals):
        sent = total_raw / (10 ** decimals)
        return False, f"Insufficient amount. Sent: {sent}, required: {expected_amount}"
    return True, "Success"


def _verify_trc20(net, txid, expected_amount):
    """Verify a TRC20 USDT transfer on TRON via the Tronscan API."""
    res = requests.get(TRONSCAN_TX_URL, params={"hash": txid}, timeout=15).json()
    if "hash" not in res:
        return False, "Transaction not found on network. It may not be confirmed yet."
    if res.get("contractRet") != "SUCCESS":
        return False, "Transaction failed on chain."

    decimals = net["decimals"]
    for t in res.get("trc20TransferInfo", []):
        if (
            t.get("to_address") == net["wallet"]
            and t.get("contract_address") == net["contract"]
        ):
            sent_raw = int(t["amount_str"])
            if sent_raw + _raw(0.001, decimals) < _raw(expected_amount, decimals):
                sent = sent_raw / (10 ** decimals)
                return False, f"Insufficient amount. Sent: {sent}, required: {expected_amount}"
            return True, "Success"
    return False, "No USDT transfer to our wallet found in this transaction."
