#!/bin/bash
# blog (c) by FriesI23
#
# blog is licensed under a
# Creative Commons Attribution-ShareAlike 4.0 International License.
#
# You should have received a copy of the license along with this
# work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.

command="bundle exec jekyll serve"

if [[ $@ == *"-p"* ]]; then
    # 如果包含，则设置 JEKYLL_ENV 为 production
    export JEKYLL_ENV=production
    echo "-> run in production"
fi

if [[ $@ == *"-d"* ]]; then
    # 如果包含, 则设置包含草稿
    command="$command --draft"
    echo "-> run with draft"
fi

eval $command
