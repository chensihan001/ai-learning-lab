$ErrorActionPreference = 'Stop'
$imgKey = '7cd084941338484aae1ad9425b84077c'
$subKey = '4932caff0ff746eab6f01bf08b70ac45'
$tab = @(46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52)
$raw = $imgKey + $subKey
$mixin = -join ($tab | ForEach-Object { $raw[$_] })
$mixin = $mixin.Substring(0,32)

function Get-Md5([string]$s) {
  $md5 = [System.Security.Cryptography.MD5]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
  return ([System.BitConverter]::ToString($md5.ComputeHash($bytes)) -replace '-','').ToLower()
}

$keywords = @(
  '大模型 应用开发 实战',
  'RAG 从零 实现',
  '手写 Agent 框架',
  'LLaMA-Factory 微调',
  'LLM 面试 八股',
  'Transformer 李沐 详解',
  '大模型 实习 面经'
)

foreach ($kw in $keywords) {
  $wts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $enc = [uri]::EscapeDataString($kw)
  # 参数按 key 排序：keyword, page, search_type, wts
  $query = "keyword=$enc&page=1&search_type=video&wts=$wts"
  $wrid = Get-Md5 ($query + $mixin)
  $url = "https://api.bilibili.com/x/web-interface/wbi/search/type?$query&w_rid=$wrid"
  Write-Output "### $kw"
  Write-Output $url
}
