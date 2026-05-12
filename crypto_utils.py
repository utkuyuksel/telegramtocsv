import requests
import config

TRONSCAN_TX_URL = "https://apilist.tronscanapi.com/api/transaction-info"
USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


def verify_txid(txid, expected_amount, currency="USDT"):
    """
    Verify a TRC20 USDT or TRX payment to the configured wallet.

    Returns (True, "Success") on success, (False, reason) on failure.
    """
    wallet = config.WALLET_ADDRESS
    if not wallet:
        return False, "Server wallet not configured."
    if not txid or len(txid) < 20:
        return False, "Invalid TXID."

    try:
        res = requests.get(TRONSCAN_TX_URL, params={"hash": txid}, timeout=15).json()

        if "hash" not in res:
            return False, "Transaction not found on network. It may not be confirmed yet."

        if res.get("contractRet") != "SUCCESS":
            return False, "Transaction failed on chain."

        real_amount = 0.0
        receiver = ""
        token_type = ""

        if currency == "USDT":
            for transfer in res.get("trc20TransferInfo", []):
                if (
                    transfer.get("to_address") == wallet
                    and transfer.get("contract_address") == USDT_TRC20_CONTRACT
                ):
                    real_amount = float(transfer["amount_str"]) / 1_000_000
                    receiver = transfer["to_address"]
                    token_type = "USDT"
                    break

        elif currency == "TRX":
            contract = res.get("contractData", {})
            if contract.get("to_address") == wallet and "amount" in contract:
                real_amount = float(contract["amount"]) / 1_000_000
                receiver = contract["to_address"]
                token_type = "TRX"

        if receiver != wallet:
            return False, "Receiver address does not match."

        if token_type != currency:
            return False, f"Currency mismatch. Expected {currency}, got {token_type or 'unknown'}."

        if real_amount + 0.001 < expected_amount:
            return (
                False,
                f"Insufficient amount. Sent: {real_amount}, required: {expected_amount}",
            )

        return True, "Success"

    except requests.RequestException as e:
        return False, f"Network error contacting Tronscan: {e}"
    except Exception as e:
        return False, f"Verification error: {e}"
