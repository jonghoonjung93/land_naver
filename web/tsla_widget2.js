// 위젯 파라미터 설정
let widget = new ListWidget();

// 배경 그라디언트 설정 (어두운 테마에 어울리는 세련된 느낌)
const gradient = new LinearGradient();
gradient.locations = [0, 1];
gradient.colors = [new Color("#2a2a2a"), new Color("#1a1a1a")];
widget.backgroundGradient = gradient;

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
  // 가격 변동에 따른 색상 및 아이콘 설정
  const isPriceUp = stockData.mod.startsWith("+");
  const priceColor = isPriceUp ? new Color("#00cc00") : new Color("#ff3333"); // 더 선명한 색상
  const arrowIcon = isPriceUp
    ? "▲" // 상승 화살표
    : "▼"; // 하락 화살표

  // 메인 스택 (수직 정렬)
  let mainStack = widget.addStack();
  mainStack.layoutVertically();
  mainStack.spacing = 3;
  mainStack.padding = 8;
  mainStack.size = new Size(155, 155); // 작은 위젯 크기에 맞게 설정

  // 심볼과 마켓 (상단, 가운데 정렬)
  let symbolStack = mainStack.addStack();
  symbolStack.layoutHorizontally();
  symbolStack.addSpacer(); // 왼쪽 여백
  let symbolText = symbolStack.addText(`${stockData.symbol} (${stockData.market})`);
  symbolText.font = Font.boldSystemFont(16);
  symbolText.textColor = new Color("#ffffff", 0.9);
  symbolStack.addSpacer(); // 오른쪽 여백

  // 가격 (한 줄로 표시, 가운데 정렬)
  let priceStack = mainStack.addStack();
  priceStack.layoutHorizontally();
  priceStack.addSpacer(); // 왼쪽 여백
  let priceText = priceStack.addText(`$${stockData.price}`);
  priceText.font = Font.semiboldSystemFont(22);
  priceText.textColor = priceColor;
  priceStack.addSpacer(); // 오른쪽 여백

  // 변동 정보 (다음 줄, 가운데 정렬)
  let changeStack = mainStack.addStack();
  changeStack.layoutHorizontally();
  changeStack.addSpacer(); // 왼쪽 여백
  let changeText = changeStack.addText(`${arrowIcon} ${stockData.mod} (${stockData.pct})`);
  changeText.font = Font.mediumSystemFont(13);
  changeText.textColor = priceColor;
  changeStack.addSpacer(); // 오른쪽 여백

  // 날짜/시간 부분의 줄간격을 늘리기 위해 추가 여백 삽입
  mainStack.addSpacer(6); // 시간 부분 위에 6px 여백 추가 (값은 조정 가능)

  // 시간 (하단, 가운데 정렬)
  let timeStack = mainStack.addStack();
  timeStack.layoutHorizontally();
  timeStack.addSpacer(); // 왼쪽 여백
  let timeText = timeStack.addText(stockData.time);
  timeText.font = Font.lightSystemFont(11);
  timeText.textColor = new Color("#aaaaaa");
  timeStack.addSpacer(); // 오른쪽 여백
} else {
  // 에러 메시지 (중앙 정렬)
  let errorStack = widget.addStack();
  errorStack.layoutVertically();
  errorStack.centerAlignContent();
  errorStack.addSpacer(); // 위쪽 여백
  let errorText = errorStack.addText("데이터를 불러올 수 없습니다");
  errorText.font = Font.mediumSystemFont(14);
  errorText.textColor = new Color("#ff5555");
  errorStack.addSpacer(); // 아래쪽 여백
}

// 위젯 새로고침 간격 설정 (1분마다)
widget.refreshAfterDate = new Date(Date.now() + 1 * 60 * 1000);

// 위젯 표시
Script.setWidget(widget);
widget.presentSmall();
