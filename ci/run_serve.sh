# blog (c) by FriesI23
#
# blog is licensed under a
# Creative Commons Attribution-ShareAlike 4.0 International License.
#
# You should have received a copy of the license along with this
# work. If not, see <https://creativecommons.org/licenses/by-sa/4.0/>.
cd `dirname "$(readlink -f "$0")"`/..
bundle exec jekyll serve
