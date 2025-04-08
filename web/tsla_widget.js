// 위젯 파라미터 설정
let widget = new ListWidget();
widget.backgroundColor = new Color("#1a1a1a");

// API 엔드포인트 설정
const API_URL = "http://land.iptime.org/tsla";

async function getStockPrice() {
  try {
    console.log("API 요청 시작: " + API_URL);
    let req = new Request(API_URL);
    req.headers = {
      "Cache-Control": "no-cache, no-store, must-revalidate",
      Pragma: "no-cache",
      Expires: "0",
    };
    let response = await req.loadString();
    console.log("API 응답: " + response);
    let json = JSON.parse(response);
    return json;
  } catch (error) {
    console.error("에러 발생: " + error);
    return null;
  }
}

// 주가 정보 가져오기
let stockData = await getStockPrice();

// 위젯에 정보 표시
if (stockData && !stockData.error) {
  // 가격 변동에 따른 색상 설정
  const isPriceUp = stockData.mod.startsWith("+");
  const priceColor = isPriceUp ? Color.green() : Color.red();

  // 심볼과 마켓 표시
  let symbolText = widget.addText(`${stockData.symbol} (${stockData.market})`);
  symbolText.font = Font.boldSystemFont(14);
  symbolText.textColor = Color.white();
  widget.addSpacer(4);

  // 가격 표시
  let priceText = widget.addText(`$${stockData.price}`);
  priceText.font = Font.systemFont(24);
  priceText.textColor = priceColor;
  widget.addSpacer(4);

  // 변동 정보 표시
  let changeText = widget.addText(`${stockData.mod} ${stockData.pct}`);
  changeText.font = Font.systemFont(14);
  changeText.textColor = priceColor;
  widget.addSpacer(4);

  // 시간 표시
  let timeText = widget.addText(stockData.time);
  timeText.font = Font.systemFont(12);
  timeText.textColor = Color.gray();
} else {
  let errorText = widget.addText("데이터를 불러올 수 없습니다");
  errorText.font = Font.systemFont(16);
  errorText.textColor = Color.red();
}

// 위젯 새로고침 간격 설정
widget.refreshAfterDate = new Date(Date.now() + 1 * 60 * 1000); // 1분마다 새로고침 시도

// 위젯 표시
Script.setWidget(widget);
widget.presentSmall();
