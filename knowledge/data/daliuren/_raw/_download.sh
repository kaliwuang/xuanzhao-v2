#!/bin/bash
# 大六壬 29 本核心古籍批量下载
set -e
cd "C:/Users/W/xuanzhao-v2/knowledge/data/daliuren/_raw/"

BASE="https://raw.githubusercontent.com/kentang2017/shushubook/main/%E5%85%AD%E5%A3%AC"

declare -A FILES=(
  ["六壬一字诀玉连环-宋-徐汶滨.txt"]="%E5%85%AD%E5%A3%AC%E4%B8%80%E5%AD%97%E8%AF%80%E7%8E%89%E8%BF%9E%E7%8E%AF-%E5%AE%8B-%E5%BE%90%E6%B1%B6%E6%BB%A8.txt"
  ["六壬兵占-明-佚名.txt"]="%E5%85%AD%E5%A3%AC%E5%85%B5%E5%8D%A0-%E6%98%8E-%E4%BD%9A%E5%90%8D.txt"
  ["六壬大全-明-郭载騋.txt"]="%E5%85%AD%E5%A3%AC%E5%A4%A7%E5%85%A8-%E6%98%8E-%E9%83%AD%E8%BD%BD%E9%A8%8B.txt"
  ["六壬存验-清-吴师青.txt"]="%E5%85%AD%E5%A3%AC%E5%AD%98%E9%AA%8C-%E6%B8%85-%E5%90%B4%E5%B8%88%E9%9D%92.txt"
  ["六壬寻源-清-张纯照.txt"]="%E5%85%AD%E5%A3%AC%E5%AF%BB%E6%BA%90-%E6%B8%85-%E5%BC%A0%E7%BA%AF%E7%85%A7.txt"
  ["六壬心镜-唐-徐道符.txt"]="%E5%85%AD%E5%A3%AC%E5%BF%83%E9%95%9C-%E5%94%90-%E5%BE%90%E9%81%93%E7%AC%A6.txt"
  ["六壬拃河棹-明-张松源.txt"]="%E5%85%AD%E5%A3%AC%E6%8B%83%E6%B2%B3%E6%A3%B9-%E6%98%8E-%E5%BC%A0%E6%9D%BE%E6%BA%90.txt"
  ["六壬括囊赋略疏--.txt"]="%E5%85%AD%E5%A3%AC%E6%8B%AC%E5%9B%8A%E8%B5%8B%E7%95%A5%E7%96%8F--.txt"
  ["六壬指南-明-陈公献.txt"]="%E5%85%AD%E5%A3%AC%E6%8C%87%E5%8D%97-%E6%98%8E-%E9%99%88%E5%85%AC%E7%8C%AE.txt"
  ["六壬指南注解-明-陈公献.txt"]="%E5%85%AD%E5%A3%AC%E6%8C%87%E5%8D%97%E6%B3%A8%E8%A7%A3-%E6%98%8E-%E9%99%88%E5%85%AC%E7%8C%AE.txt"
  ["六壬断案-宋-邵彦和.txt"]="%E5%85%AD%E5%A3%AC%E6%96%AD%E6%A1%88-%E5%AE%8B-%E9%82%B5%E5%BD%A6%E5%92%8C.txt"
  ["六壬灵觉经--佚名.txt"]="%E5%85%AD%E5%A3%AC%E7%81%B5%E8%A7%89%E7%BB%8F--%E4%BD%9A%E5%90%8D.txt"
  ["六壬直指御定-清-佚名.txt"]="%E5%85%AD%E5%A3%AC%E7%9B%B4%E6%8C%87%E5%BE%A1%E5%AE%9A-%E6%B8%85-%E4%BD%9A%E5%90%8D.txt"
  ["六壬神定经-宋-扬维德.txt"]="%E5%85%AD%E5%A3%AC%E7%A5%9E%E5%AE%9A%E7%BB%8F-%E5%AE%8B-%E6%89%AC%E7%BB%B4%E5%BE%B7.txt"
  ["六壬神将释-明-佚名.txt"]="%E5%85%AD%E5%A3%AC%E7%A5%9E%E5%B0%86%E9%87%8A-%E6%98%8E-%E4%BD%9A%E5%90%8D.txt"
  ["六壬神课金口诀古本--佚名.txt"]="%E5%85%AD%E5%A3%AC%E7%A5%9E%E8%AF%BE%E9%87%91%E5%8F%A3%E8%AF%80%E5%8F%A4%E6%9C%AC--%E4%BD%9A%E5%90%8D.txt"
  ["六壬秘本-清-金正音.txt"]="%E5%85%AD%E5%A3%AC%E7%A7%98%E6%9C%AC-%E6%B8%85-%E9%87%91%E6%AD%A3%E9%9F%B3.txt"
  ["六壬管辂神书-三国-管辂.txt"]="%E5%85%AD%E5%A3%AC%E7%AE%A1%E8%BE%82%E7%A5%9E%E4%B9%A6-%E4%B8%89%E5%9B%BD-%E7%AE%A1%E8%BE%82.txt"
  ["六壬粹言-清-刘赤江.txt"]="%E5%85%AD%E5%A3%AC%E7%B2%B9%E8%A8%80-%E6%B8%85-%E5%88%98%E8%B5%A4%E6%B1%9F.txt"
  ["六壬经纬-清-京江铁瓮子.txt"]="%E5%85%AD%E5%A3%AC%E7%BB%8F%E7%BA%AC-%E6%B8%85-%E4%BA%AC%E6%B1%9F%E9%93%81%E7%93%AE%E5%AD%90.txt"
  ["六壬翠雨歌-明-高大器.txt"]="%E5%85%AD%E5%A3%AC%E7%BF%A0%E9%9B%A8%E6%AD%8C-%E6%98%8E-%E9%AB%98%E5%A4%A7%E5%99%A8.txt"
  ["六壬苗公射覆鬼撮脚--佚名.txt"]="%E5%85%AD%E5%A3%AC%E8%8B%97%E5%85%AC%E5%B0%84%E8%A6%86%E9%AC%BC%E6%92%AE%E8%84%9A--%E4%BD%9A%E5%90%8D.txt"
  ["六壬论命秘要--佚名.txt"]="%E5%85%AD%E5%A3%AC%E8%AE%BA%E5%91%BD%E7%A7%98%E8%A6%81--%E4%BD%9A%E5%90%8D.txt"
  ["六壬金铰剪--徐养浩.txt"]="%E5%85%AD%E5%A3%AC%E9%87%91%E9%93%B0%E5%89%AA--%E5%BE%90%E5%85%BB%E6%B5%A9.txt"
  ["六壬银河櫂--佚名.txt"]="%E5%85%AD%E5%A3%AC%E9%93%B6%E6%B2%B3%E6%AB%82--%E4%BD%9A%E5%90%8D.txt"
  ["六壬集成五要权衡--佚名.txt"]="%E5%85%AD%E5%A3%AC%E9%9B%86%E6%88%90%E4%BA%94%E8%A6%81%E6%9D%83%E8%A1%A1--%E4%BD%9A%E5%90%8D.txt"
  ["壬占汇选-清-程树勋.txt"]="%E5%A3%AC%E5%8D%A0%E6%B1%87%E9%80%89-%E6%B8%85-%E7%A8%8B%E6%A0%91%E5%8B%8B.txt"
  ["壬学琐记-清-程树勋.txt"]="%E5%A3%AC%E5%AD%A6%E7%90%90%E8%AE%B0-%E6%B8%85-%E7%A8%8B%E6%A0%91%E5%8B%8B.txt"
  ["壬归-清-佚名.txt"]="%E5%A3%AC%E5%BD%92-%E6%B8%85-%E4%BD%9A%E5%90%8D.txt"
)

for name in "${!FILES[@]}"; do
  url="$BASE/${FILES[$name]}"
  echo "下载: $name"
  curl -sL --max-time 120 -o "$name" "$url"
done

echo ""
echo "=== 全部下载完成 ==="
ls -la